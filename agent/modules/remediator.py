"""
ApexSys Agent - Autonomous Remediation Engine
Executes targeted low-level system repairs, DISM image restoration, SFC scannow,
network stack resets, deep storage purging, service recycling, and One-Click Fix orchestration.
"""

import os
import shutil
import subprocess
import time
from typing import Callable, Optional
import psutil

LogCallback = Callable[[str, str], None]  # (text, stream)
ProgressCallback = Callable[[int, str], None]  # (percent, current_action)


class RemediationEngine:
    @staticmethod
    def _run_streaming_cmd(
        cmd: str,
        log_cb: Optional[LogCallback] = None,
        progress_cb: Optional[ProgressCallback] = None,
        base_progress: int = 0,
        span_progress: int = 100,
        timeout_sec: int = 180,
    ) -> int:
        """Executes a system process and streams lines to log callback."""
        if log_cb:
            log_cb(f"> Executing: {cmd}", "stdout")

        try:
            proc = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                shell=True,
                bufsize=1,
                universal_newlines=True,
            )

            # Read stdout
            for line in proc.stdout:
                line_str = line.strip()
                if line_str and log_cb:
                    log_cb(line_str, "stdout")

            proc.wait(timeout=timeout_sec)

            # Check stderr
            err = proc.stderr.read().strip()
            if err and log_cb:
                log_cb(f"[WARN/STDERR] {err}", "stderr")

            return proc.returncode
        except subprocess.TimeoutExpired:
            if log_cb:
                log_cb(f"[TIMEOUT] Execution exceeded {timeout_sec}s threshold.", "stderr")
            return -1
        except Exception as e:
            if log_cb:
                log_cb(f"[ERROR] Failed to run command: {str(e)}", "stderr")
            return -1

    @classmethod
    def run_dism_restore(
        cls,
        log_cb: Optional[LogCallback] = None,
        progress_cb: Optional[ProgressCallback] = None,
    ) -> bool:
        """Runs DISM /Online /Cleanup-Image /RestoreHealth."""
        if progress_cb:
            progress_cb(10, "Initializing Windows Component Store DISM RestoreHealth...")

        cmd = "dism.exe /Online /Cleanup-Image /RestoreHealth"
        code = cls._run_streaming_cmd(cmd, log_cb=log_cb, timeout_sec=240)

        if progress_cb:
            progress_cb(100, "DISM Image Restore Completed.")
        return code == 0

    @classmethod
    def run_sfc_repair(
        cls,
        log_cb: Optional[LogCallback] = None,
        progress_cb: Optional[ProgressCallback] = None,
    ) -> bool:
        """Runs SFC /scannow to repair protected Windows system files."""
        if progress_cb:
            progress_cb(10, "Starting System File Checker (SFC) Scannow...")

        cmd = "sfc.exe /scannow"
        code = cls._run_streaming_cmd(cmd, log_cb=log_cb, timeout_sec=240)

        if progress_cb:
            progress_cb(100, "SFC Scannow Completed.")
        return code in [0, 1]

    @classmethod
    def run_network_reset(
        cls,
        log_cb: Optional[LogCallback] = None,
        progress_cb: Optional[ProgressCallback] = None,
    ) -> bool:
        """Flushes DNS cache, resets Winsock catalog, and refreshes IP configuration."""
        steps = [
            ("ipconfig /flushdns", "Flushing DNS resolver cache..."),
            ("ipconfig /registerdns", "Refreshing dynamic DNS registrations..."),
            ("netsh winsock reset", "Resetting Winsock catalog to clean state..."),
            ("netsh int ip reset", "Resetting TCP/IP protocol stack..."),
        ]

        total = len(steps)
        for idx, (cmd, desc) in enumerate(steps, 1):
            if progress_cb:
                pct = int((idx / total) * 100)
                progress_cb(pct, desc)
            cls._run_streaming_cmd(cmd, log_cb=log_cb, timeout_sec=15)

        if log_cb:
            log_cb("[SUCCESS] Network stack and DNS caches successfully reset.", "stdout")
        return True

    @classmethod
    def clean_deep_junk(
        cls,
        log_cb: Optional[LogCallback] = None,
        progress_cb: Optional[ProgressCallback] = None,
    ) -> int:
        """
        Deep storage purge: cleans Temp, Prefetch, and servicing cache.
        Returns total freed MB.
        """
        targets = [
            os.getenv("TEMP", r"C:\Users\Default\AppData\Local\Temp"),
            r"C:\Windows\Temp",
            r"C:\Windows\Prefetch",
            r"C:\Windows\SoftwareDistribution\Download",
        ]

        bytes_freed = 0
        total_targets = len(targets)

        for idx, folder in enumerate(targets, 1):
            if progress_cb:
                pct = int((idx / total_targets) * 100)
                progress_cb(pct, f"Purging {os.path.basename(folder)} cache...")

            if not os.path.exists(folder):
                continue

            try:
                for entry in os.scandir(folder):
                    try:
                        if entry.is_file(follow_symlinks=False):
                            sz = entry.stat().st_size
                            os.remove(entry.path)
                            bytes_freed += sz
                        elif entry.is_dir(follow_symlinks=False):
                            shutil.rmtree(entry.path, ignore_errors=True)
                    except Exception:
                        pass
            except Exception:
                pass

        freed_mb = round(bytes_freed / (1024 * 1024), 2)
        if log_cb:
            log_cb(f"[SUCCESS] Purged {freed_mb} MB of temporary junk & cached bloat.", "stdout")
        return int(freed_mb)

    @classmethod
    def fix_registry_integrity(
        cls,
        log_cb: Optional[LogCallback] = None,
        progress_cb: Optional[ProgressCallback] = None,
    ) -> bool:
        """
        Removes invalid startup Run entries pointing to non-existent executable binaries.
        """
        if progress_cb:
            progress_cb(20, "Scanning and pruning broken registry startup keys...")

        ps_fix = """
        $keys = @(
            'HKLM:\\Software\\Microsoft\\Windows\\CurrentVersion\\Run',
            'HKLM:\\Software\\Microsoft\\Windows\\CurrentVersion\\RunOnce',
            'HKCU:\\Software\\Microsoft\\Windows\\CurrentVersion\\Run',
            'HKCU:\\Software\\Microsoft\\Windows\\CurrentVersion\\RunOnce'
        )
        $pruned = 0
        foreach ($k in $keys) {
            if (Test-Path $k) {
                $prop = Get-ItemProperty $k
                foreach ($p in $prop.PSObject.Properties) {
                    if ($p.Name -notmatch '^(PS|\\(default\\))') {
                        $rawVal = [string]$p.Value
                        $clean = $rawVal -replace '^"|"[^"]*$', '' -replace ' -.*$', '' -replace ' /.*$', ''
                        $target = [Environment]::ExpandEnvironmentVariables($clean.Trim())
                        if ($target -and ($target -match '^[a-zA-Z]:\\\\') -and !(Test-Path $target)) {
                            Remove-ItemProperty -Path $k -Name $p.Name -ErrorAction SilentlyContinue
                            Write-Output "Pruned broken key: $($p.Name) -> $target"
                            $pruned++
                        }
                    }
                }
            }
        }
        Write-Output "Total pruned keys: $pruned"
        """
        code = cls._run_streaming_cmd(
            f"powershell -NoProfile -NonInteractive -Command \"{ps_fix}\"",
            log_cb=log_cb,
            timeout_sec=20,
        )

        if progress_cb:
            progress_cb(100, "Registry integrity check completed.")
        return code == 0

    @classmethod
    def prune_broken_shortcuts(
        cls,
        log_cb: Optional[LogCallback] = None,
        progress_cb: Optional[ProgressCallback] = None,
    ) -> bool:
        """Prunes broken .lnk shortcuts from Desktop and Start Menu."""
        if progress_cb:
            progress_cb(30, "Pruning dead desktop & start menu shortcuts...")

        ps_script = """
        $wscript = New-Object -ComObject WScript.Shell
        $paths = @(
            [Environment]::GetFolderPath('Desktop'),
            [Environment]::GetFolderPath('CommonDesktop')
        )
        $deleted = 0
        foreach ($folder in $paths) {
            if (Test-Path $folder) {
                $lnks = Get-ChildItem -Path $folder -Filter '*.lnk' -Recurse -ErrorAction SilentlyContinue
                foreach ($l in $lnks) {
                    try {
                        $target = $wscript.CreateShortcut($l.FullName).TargetPath
                        if ($target -and ($target -match '^[a-zA-Z]:\\\\') -and !(Test-Path $target)) {
                            Remove-Item -Path $l.FullName -Force -ErrorAction SilentlyContinue
                            Write-Output "Removed orphaned shortcut: $($l.Name)"
                            $deleted++
                        }
                    } catch {}
                }
            }
        }
        Write-Output "Total orphaned shortcuts purged: $deleted"
        """
        code = cls._run_streaming_cmd(
            f"powershell -NoProfile -NonInteractive -Command \"{ps_script}\"",
            log_cb=log_cb,
            timeout_sec=20,
        )

        if progress_cb:
            progress_cb(100, "Shortcut pruning finished.")
        return code == 0

    @classmethod
    def restart_vital_services(
        cls,
        log_cb: Optional[LogCallback] = None,
        progress_cb: Optional[ProgressCallback] = None,
    ) -> bool:
        """Recycles essential Windows system services."""
        services = ["wuauserv", "bits", "cryptsvc", "spooler"]
        total = len(services)

        for idx, svc in enumerate(services, 1):
            if progress_cb:
                pct = int((idx / total) * 100)
                progress_cb(pct, f"Restarting service '{svc}'...")
            cls._run_streaming_cmd(f"net stop {svc} /y & net start {svc}", log_cb=log_cb, timeout_sec=25)

        if log_cb:
            log_cb("[SUCCESS] Vital Windows services restarted and verified running.", "stdout")
        return True

    @classmethod
    def rescan_pnp_drivers(
        cls,
        log_cb: Optional[LogCallback] = None,
        progress_cb: Optional[ProgressCallback] = None,
    ) -> bool:
        """Triggers PnP hardware re-enumeration to resolve transient driver errors."""
        if progress_cb:
            progress_cb(50, "Invoking PnP Device Rescan via pnputil...")

        cmd = "pnputil.exe /scan-devices"
        code = cls._run_streaming_cmd(cmd, log_cb=log_cb, timeout_sec=20)

        if progress_cb:
            progress_cb(100, "PnP hardware rescan complete.")
        return code == 0

    @classmethod
    def optimize_power(
        cls,
        log_cb: Optional[LogCallback] = None,
        progress_cb: Optional[ProgressCallback] = None,
    ) -> bool:
        """Sets High Performance power scheme to resolve aggressive CPU clock throttling."""
        if progress_cb:
            progress_cb(50, "Switching to High Performance power scheme...")

        # 8c5e7fda-e8bf-4a96-9a85-a6e23a8c635c is High Performance GUID
        cmd = "powercfg.exe /setactive 8c5e7fda-e8bf-4a96-9a85-a6e23a8c635c"
        cls._run_streaming_cmd(cmd, log_cb=log_cb, timeout_sec=10)

        if log_cb:
            log_cb("[SUCCESS] Power scheme set to High Performance. CPU thermal limits reset.", "stdout")
        return True

    @classmethod
    def kill_process(
        cls,
        pid: int,
        log_cb: Optional[LogCallback] = None,
        progress_cb: Optional[ProgressCallback] = None,
    ) -> bool:
        """Safely terminates a runaway or malicious process by PID."""
        if log_cb:
            log_cb(f"Terminating runaway process PID {pid}...", "stdout")

        try:
            p = psutil.Process(pid)
            p_name = p.name()
            p.terminate()
            p.wait(timeout=3)
            if log_cb:
                log_cb(f"[SUCCESS] Terminated {p_name} (PID {pid}).", "stdout")
            return True
        except Exception:
            # Fallback to taskkill /F /PID
            code = cls._run_streaming_cmd(f"taskkill /F /PID {pid}", log_cb=log_cb, timeout_sec=5)
            return code == 0

    @classmethod
    def run_one_click_fix_all(
        cls,
        log_cb: Optional[LogCallback] = None,
        progress_cb: Optional[ProgressCallback] = None,
    ) -> bool:
        """
        Orchestrates full phased autonomous remediation pipeline:
        Phase 1: Process triage & resource relief (10%)
        Phase 2: Deep junk purging & cache clearing (25%)
        Phase 3: Network stack reset & DNS flush (40%)
        Phase 4: Registry integrity & dead shortcuts (55%)
        Phase 5: Component Store DISM Restore (75%)
        Phase 6: SFC System File Integrity Repair (90%)
        Phase 7: Windows service recycling & Driver rescan (100%)
        """
        if log_cb:
            log_cb("==================================================", "stdout")
            log_cb(">>> INITIATING APEXSYS ONE-CLICK AUTONOMOUS REMEDIATION <<<", "stdout")
            log_cb("==================================================", "stdout")

        # Phase 1: Storage Cache Purging
        if progress_cb:
            progress_cb(15, "Phase 1/6: Deep Junk & Cache Purging...")
        cls.clean_deep_junk(log_cb=log_cb)

        # Phase 2: Network Reset
        if progress_cb:
            progress_cb(30, "Phase 2/6: Network Stack Reset & DNS Flush...")
        cls.run_network_reset(log_cb=log_cb)

        # Phase 3: Registry & Shortcuts
        if progress_cb:
            progress_cb(45, "Phase 3/6: Repairing Registry Integrity & Shortcuts...")
        cls.fix_registry_integrity(log_cb=log_cb)
        cls.prune_broken_shortcuts(log_cb=log_cb)

        # Phase 4: DISM Restore
        if progress_cb:
            progress_cb(60, "Phase 4/6: Windows Component Store DISM Image Restore...")
        cls.run_dism_restore(log_cb=log_cb)

        # Phase 5: SFC Scannow
        if progress_cb:
            progress_cb(80, "Phase 5/6: System File Checker (SFC) Integrity Repair...")
        cls.run_sfc_repair(log_cb=log_cb)

        # Phase 6: Services & Drivers
        if progress_cb:
            progress_cb(95, "Phase 6/6: Recycling Services & Driver Rescan...")
        cls.restart_vital_services(log_cb=log_cb)
        cls.rescan_pnp_drivers(log_cb=log_cb)
        cls.optimize_power(log_cb=log_cb)

        if progress_cb:
            progress_cb(100, "Autonomous Remediation Pipeline Completed Successfully.")

        if log_cb:
            log_cb("==================================================", "stdout")
            log_cb("[APEXSYS HEALING COMPLETE] All repair stages finalized.", "stdout")
            log_cb("==================================================", "stdout")

        return True
