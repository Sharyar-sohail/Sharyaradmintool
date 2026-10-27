"""
ApexSys Agent - OS & File System Integrity Module
Executes/parses DISM and SFC status, audits CBS servicing logs, scans registry
startup consistency, identifies orphaned shortcuts, and measures deep junk bloat.
"""

import ctypes
import os
import re
import shutil
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Tuple


class OSIntegrityDiagnostics:
    @staticmethod
    def is_admin() -> bool:
        """Check if current agent process has Administrator elevation."""
        try:
            return ctypes.windll.shell32.IsUserAnAdmin() != 0
        except Exception:
            return False

    @classmethod
    def check_dism_health(cls) -> Dict[str, Any]:
        """
        Check Windows Component Store corruption using DISM CheckHealth or CBS logs.
        """
        result = {
            "dism_corrupted": False,
            "dism_status": "Healthy",
            "component_store_status": "No component store corruption detected.",
            "can_restore": True,
        }

        # Attempt DISM /Online /Cleanup-Image /CheckHealth
        try:
            cmd = "dism.exe /Online /Cleanup-Image /CheckHealth"
            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                shell=True,
                timeout=25
            )
            out = proc.stdout

            if "No component store corruption detected" in out:
                result["dism_corrupted"] = False
                result["dism_status"] = "Healthy"
            elif "The component store is repairable" in out or "component store is corrupted" in out:
                result["dism_corrupted"] = True
                result["dism_status"] = "Repairable Corruption"
                result["component_store_status"] = "Component store is corrupted and repairable."
            elif proc.returncode != 0:
                # If un-elevated (error 740), inspect CBS log as fallback
                cbs_res = cls._check_cbs_for_dism_corruption()
                result.update(cbs_res)
        except Exception:
            cbs_res = cls._check_cbs_for_dism_corruption()
            result.update(cbs_res)

        return result

    @classmethod
    def _check_cbs_for_dism_corruption(cls) -> Dict[str, Any]:
        """Inspect CBS.log for package store corruption flags."""
        cbs_path = r"C:\Windows\Logs\CBS\CBS.log"
        if not os.path.exists(cbs_path):
            return {"dism_corrupted": False, "dism_status": "Unverified (CBS Log Absent)"}

        try:
            with open(cbs_path, "r", encoding="utf-8", errors="ignore") as f:
                # Read last 3000 lines
                lines = f.readlines()[-3000:]
                content = "".join(lines)
                if "Failed to pin down package" in content or "Corrupt component store" in content:
                    return {
                        "dism_corrupted": True,
                        "dism_status": "CBS Log Flags Store Corruption",
                        "component_store_status": "CBS log contains component store errors.",
                    }
        except Exception:
            pass

        return {"dism_corrupted": False, "dism_status": "Healthy (CBS Log Analysis)"}

    @classmethod
    def check_sfc_and_cbs(cls) -> Dict[str, Any]:
        """
        Check CBS.log for System File Checker (SFC) integrity violations and error count.
        """
        result = {
            "sfc_corrupted": False,
            "corrupted_files_count": 0,
            "corrupted_files": [],
            "cbs_error_count": 0,
        }

        cbs_path = r"C:\Windows\Logs\CBS\CBS.log"
        if not os.path.exists(cbs_path):
            return result

        try:
            with open(cbs_path, "r", encoding="utf-8", errors="ignore") as f:
                lines = f.readlines()[-4000:]

            cbs_errors = 0
            corrupted = []

            for line in lines:
                if ", Error " in line or " CBS Error " in line:
                    cbs_errors += 1
                if "[SR] Cannot repair member file" in line:
                    # Extract file name
                    m = re.search(r'\[SR\] Cannot repair member file \[(.*?)\]', line)
                    if m:
                        fname = m.group(1).split(",")[0]
                        if fname not in corrupted:
                            corrupted.append(fname)
                    else:
                        corrupted.append(line.strip()[-50:])

            result["cbs_error_count"] = cbs_errors
            if corrupted:
                result["sfc_corrupted"] = True
                result["corrupted_files_count"] = len(corrupted)
                result["corrupted_files"] = corrupted[:10]
        except Exception:
            pass

        return result

    @classmethod
    def audit_registry_run_keys(cls) -> List[Dict[str, Any]]:
        """
        Audits startup Run keys in HKLM and HKCU. Flags broken paths where target binary is missing.
        """
        broken_keys = []
        ps_audit = """
        $keys = @(
            'HKLM:\\Software\\Microsoft\\Windows\\CurrentVersion\\Run',
            'HKLM:\\Software\\Microsoft\\Windows\\CurrentVersion\\RunOnce',
            'HKCU:\\Software\\Microsoft\\Windows\\CurrentVersion\\Run',
            'HKCU:\\Software\\Microsoft\\Windows\\CurrentVersion\\RunOnce',
            'HKLM:\\Software\\WOW6432Node\\Microsoft\\Windows\\CurrentVersion\\Run'
        )
        $results = @()
        foreach ($k in $keys) {
            if (Test-Path $k) {
                $prop = Get-ItemProperty $k
                foreach ($p in $prop.PSObject.Properties) {
                    if ($p.Name -notmatch '^(PS|\\(default\\))') {
                        $rawVal = [string]$p.Value
                        $clean = $rawVal -replace '^"|"[^"]*$', '' -replace ' -.*$', '' -replace ' /.*$', ''
                        $results += [PSCustomObject]@{
                            Hive = $k
                            KeyName = $p.Name
                            Command = $rawVal
                            TargetFile = $clean.Trim()
                        }
                    }
                }
            }
        }
        $results | ConvertTo-Json -Compress
        """
        try:
            full_cmd = f"powershell -NoProfile -NonInteractive -Command \"{ps_audit}\""
            res = subprocess.run(full_cmd, capture_output=True, text=True, timeout=10, shell=True)
            out = res.stdout.strip()
            if out and out != "null":
                import json
                entries = json.loads(out)
                if isinstance(entries, dict):
                    entries = [entries]
                for item in entries:
                    target = item.get("TargetFile", "")
                    # Expand environment variables like %ProgramFiles%
                    expanded = os.path.expandvars(target)
                    if expanded and not os.path.exists(expanded) and ":" in expanded:
                        broken_keys.append({
                            "hive": item.get("Hive"),
                            "name": item.get("KeyName"),
                            "command": item.get("Command"),
                            "missing_path": expanded,
                        })
        except Exception:
            pass

        return broken_keys

    @classmethod
    def audit_orphaned_shortcuts(cls) -> List[Dict[str, Any]]:
        """
        Audits Desktop and Start Menu for dead .lnk files.
        """
        broken_shortcuts = []
        ps_script = """
        $wscript = New-Object -ComObject WScript.Shell
        $paths = @(
            [Environment]::GetFolderPath('Desktop'),
            [Environment]::GetFolderPath('CommonDesktop'),
            [Environment]::GetFolderPath('StartMenu'),
            [Environment]::GetFolderPath('CommonStartMenu')
        )
        $broken = @()
        foreach ($folder in $paths) {
            if (Test-Path $folder) {
                $lnks = Get-ChildItem -Path $folder -Filter '*.lnk' -Recurse -ErrorAction SilentlyContinue | Select-Object -First 50
                foreach ($l in $lnks) {
                    try {
                        $target = $wscript.CreateShortcut($l.FullName).TargetPath
                        if ($target -and ($target -match '^[a-zA-Z]:\\\\') -and !(Test-Path $target)) {
                            $broken += [PSCustomObject]@{
                                ShortcutPath = $l.FullName
                                BrokenTarget = $target
                                FileName = $l.Name
                            }
                        }
                    } catch {}
                }
            }
        }
        $broken | ConvertTo-Json -Compress
        """
        try:
            full_cmd = f"powershell -NoProfile -NonInteractive -Command \"{ps_script}\""
            res = subprocess.run(full_cmd, capture_output=True, text=True, timeout=12, shell=True)
            out = res.stdout.strip()
            if out and out != "null":
                import json
                items = json.loads(out)
                if isinstance(items, dict):
                    items = [items]
                for it in items:
                    broken_shortcuts.append({
                        "file_name": it.get("FileName"),
                        "shortcut_path": it.get("ShortcutPath"),
                        "broken_target": it.get("BrokenTarget"),
                    })
        except Exception:
            pass

        return broken_shortcuts

    @classmethod
    def calculate_deep_junk_mb(cls) -> Dict[str, Any]:
        """
        Calculates size of temp caches, Prefetch, and servicing cache.
        """
        targets = {
            "user_temp": os.getenv("TEMP", r"C:\Users\Default\AppData\Local\Temp"),
            "windows_temp": r"C:\Windows\Temp",
            "prefetch": r"C:\Windows\Prefetch",
            "softwaredist_download": r"C:\Windows\SoftwareDistribution\Download",
        }

        total_bytes = 0
        breakdown = {}

        for name, folder in targets.items():
            folder_bytes = 0
            if os.path.exists(folder):
                try:
                    for root, _, files in os.walk(folder):
                        for f in files:
                            try:
                                fp = os.path.join(root, f)
                                folder_bytes += os.path.getsize(fp)
                            except Exception:
                                pass
                except Exception:
                    pass
            mb = round(folder_bytes / (1024 * 1024), 1)
            breakdown[name] = mb
            total_bytes += folder_bytes

        total_mb = round(total_bytes / (1024 * 1024), 1)
        return {
            "total_junk_mb": total_mb,
            "breakdown_mb": breakdown,
        }

    @classmethod
    def get_logical_storage_status(cls) -> Dict[str, Any]:
        """
        Examines storage capacity across all active logical drives.
        """
        drives = []
        low_space_drives = []

        try:
            for letter in "CDEFGHIJKLMNOPQRSTUVWXYZ":
                drive_path = f"{letter}:\\"
                if os.path.exists(drive_path):
                    try:
                        total, used, free = shutil.disk_usage(drive_path)
                        total_gb = round(total / (1024 ** 3), 1)
                        free_gb = round(free / (1024 ** 3), 1)
                        used_gb = round(used / (1024 ** 3), 1)
                        free_pct = round((free / total) * 100, 1) if total > 0 else 0

                        d_info = {
                            "letter": letter,
                            "total_gb": total_gb,
                            "used_gb": used_gb,
                            "free_gb": free_gb,
                            "free_pct": free_pct,
                        }
                        drives.append(d_info)

                        if free_pct < 12.0 or free_gb < 10.0:
                            low_space_drives.append(d_info)
                    except Exception:
                        pass
        except Exception:
            pass

        return {
            "drives": drives,
            "low_space_drives": low_space_drives,
        }

    @classmethod
    def run_full_scan(cls) -> Dict[str, Any]:
        """Run all OS integrity and storage diagnostic tests."""
        dism = cls.check_dism_health()
        sfc = cls.check_sfc_and_cbs()
        broken_reg = cls.audit_registry_run_keys()
        broken_lnks = cls.audit_orphaned_shortcuts()
        junk = cls.calculate_deep_junk_mb()
        storage = cls.get_logical_storage_status()

        return {
            "dism": dism,
            "sfc": sfc,
            "broken_registry_keys": broken_reg,
            "broken_shortcuts": broken_lnks,
            "junk_metrics": junk,
            "storage_metrics": storage,
            "is_admin": cls.is_admin(),
        }
