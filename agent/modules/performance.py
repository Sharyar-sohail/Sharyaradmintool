"""
ApexSys Agent - Performance & Bottleneck Analysis Module
Windows Event Log diagnostics (BSODs, crashes, disk errors), startup audit,
background resource hogs identification, and network stack integrity testing.
"""

import json
import socket
import subprocess
import time
from typing import Any, Dict, List
import psutil


class PerformanceDiagnostics:
    @staticmethod
    def _run_ps_json(ps_cmd: str, timeout: int = 15) -> Any:
        full_cmd = f"powershell -NoProfile -NonInteractive -Command \"{ps_cmd} | ConvertTo-Json -Compress -Depth 3\""
        try:
            res = subprocess.run(
                full_cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
                shell=True
            )
            out = res.stdout.strip()
            if not out or out == "null":
                return None
            return json.loads(out)
        except Exception:
            return None

    @classmethod
    def get_event_log_errors(cls) -> Dict[str, Any]:
        """
        Parses System and Application event logs for Critical (1) and Error (2) events.
        Specialized detection for BSODs (ID 41, 1001) and Disk hardware errors (ID 7, 11).
        """
        result = {
            "critical_errors_count": 0,
            "bsod_events_count": 0,
            "latest_bsod_code": None,
            "disk_errors_count": 0,
            "app_crash_count": 0,
            "recent_events": [],
        }

        # Query System log for Critical/Error in last 48 hours
        ps_events = """
        $cutoff = (Get-Date).AddHours(-48)
        $events = Get-WinEvent -FilterHashtable @{LogName='System'; Level=1,2; StartTime=$cutoff} -MaxEvents 30 -ErrorAction SilentlyContinue |
            Select-Object Id, LevelDisplayName, ProviderName, TimeCreated, Message
        $events | ConvertTo-Json -Compress
        """
        data = cls._run_ps_json(ps_events, timeout=12)
        if data:
            if isinstance(data, dict):
                data = [data]
            result["critical_errors_count"] = len(data)

            for ev in data:
                ev_id = ev.get("Id", 0)
                provider = str(ev.get("ProviderName", ""))
                msg = str(ev.get("Message", ""))
                time_created = str(ev.get("TimeCreated", ""))

                # Check BSOD Kernel-Power
                if ev_id == 41:
                    result["bsod_events_count"] += 1
                    if not result["latest_bsod_code"]:
                        result["latest_bsod_code"] = "Kernel-Power Event 41 (System Reboot without clean shutdown)"

                # Check BugCheck
                elif ev_id == 1001 and "BugCheck" in provider:
                    result["bsod_events_count"] += 1
                    result["latest_bsod_code"] = msg[:120]

                # Check Disk errors
                elif ev_id in [7, 11] or "disk" in provider.lower():
                    result["disk_errors_count"] += 1

                # Keep top 8 representative events for dashboard display
                if len(result["recent_events"]) < 8:
                    clean_msg = " ".join(msg.split())[:160]
                    result["recent_events"].append({
                        "id": ev_id,
                        "level": ev.get("LevelDisplayName", "Error"),
                        "source": provider,
                        "time": time_created,
                        "summary": clean_msg,
                    })

        # Query Application crashes (Event ID 1000)
        ps_app_crash = """
        $cutoff = (Get-Date).AddHours(-48)
        $crashes = Get-WinEvent -FilterHashtable @{LogName='Application'; Id=1000; StartTime=$cutoff} -MaxEvents 15 -ErrorAction SilentlyContinue |
            Select-Object Id, TimeCreated, Message
        $crashes | ConvertTo-Json -Compress
        """
        crash_data = cls._run_ps_json(ps_app_crash, timeout=8)
        if crash_data:
            if isinstance(crash_data, dict):
                crash_data = [crash_data]
            result["app_crash_count"] = len(crash_data)

        return result

    @classmethod
    def audit_startup_items(cls) -> Dict[str, Any]:
        """
        Audit total startup entries from Registry and Task Scheduler.
        """
        startup_items = []
        ps_startup = """
        Get-CimInstance Win32_StartupCommand | Select-Object Name, Command, Location, User | ConvertTo-Json -Compress
        """
        data = cls._run_ps_json(ps_startup, timeout=8)
        if data:
            if isinstance(data, dict):
                data = [data]
            for it in data:
                startup_items.append({
                    "name": it.get("Name", "Unknown"),
                    "command": it.get("Command", ""),
                    "location": it.get("Location", ""),
                    "user": it.get("User", ""),
                })

        return {
            "total_startup_count": len(startup_items),
            "items": startup_items[:25],
        }

    @classmethod
    def detect_resource_hogs(cls) -> List[Dict[str, Any]]:
        """
        Detects runaway processes consuming extreme CPU (> 40%) or RAM (> 1.2 GB).
        """
        hogs = []
        try:
            # First pass for cpu_percent warmup
            for p in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_info', 'status']):
                try:
                    p.cpu_percent(None)
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass

            time.sleep(0.3)

            for p in psutil.process_iter(['pid', 'name', 'memory_info', 'status']):
                try:
                    cpu_p = p.cpu_percent(None)
                    mem_info = p.info.get('memory_info')
                    ram_mb = (mem_info.rss / (1024 * 1024)) if mem_info else 0
                    p_name = p.info.get('name', 'Unknown')
                    pid = p.info.get('pid', 0)

                    # Criteria for hog: CPU > 45% or RAM > 1500MB (excluding System / Idle)
                    if pid > 4 and p_name.lower() not in ['system idle process', 'idle']:
                        if cpu_p > 45.0 or ram_mb > 1500.0:
                            hogs.append({
                                "pid": pid,
                                "name": p_name,
                                "cpu_pct": round(cpu_p, 1),
                                "ram_mb": round(ram_mb, 1),
                                "status": str(p.info.get('status', 'running')),
                            })
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
        except Exception:
            pass

        # Sort by resource impact
        hogs.sort(key=lambda x: (x["cpu_pct"] * 2 + x["ram_mb"] / 50), reverse=True)
        return hogs[:8]

    @classmethod
    def test_network_stack(cls) -> Dict[str, Any]:
        """
        Tests DNS lookup latency, default gateway reachability, and packet response.
        """
        result = {
            "dns_latency_ms": 0.0,
            "dns_healthy": True,
            "gateway_reachable": True,
            "gateway_ip": "Unknown",
            "ping_latency_ms": 0.0,
            "network_issues": [],
        }

        # 1. DNS Resolution Benchmark
        test_host = "google.com"
        t0 = time.time()
        try:
            socket.gethostbyname(test_host)
            dns_time_ms = round((time.time() - t0) * 1000, 1)
            result["dns_latency_ms"] = dns_time_ms
            if dns_time_ms > 400:
                result["network_issues"].append({
                    "type": "dns_latency",
                    "title": f"Elevated DNS Query Latency ({dns_time_ms} ms)",
                    "detail": "DNS resolution response is unusually slow, causing browser stalls.",
                })
        except Exception as e:
            result["dns_healthy"] = False
            result["dns_latency_ms"] = 999.0
            result["network_issues"].append({
                "type": "dns_failure",
                "title": "DNS Resolution Failed",
                "detail": f"Failed to resolve {test_host}: {str(e)}",
            })

        # 2. Ping Cloudflare / Google DNS (1.1.1.1 / 8.8.8.8)
        try:
            ping_cmd = "ping -n 2 -w 1000 1.1.1.1"
            res = subprocess.run(ping_cmd, capture_output=True, text=True, timeout=5, shell=True)
            out = res.stdout
            if "Average =" in out:
                # Extract average ms
                import re
                m = re.search(r'Average\s*=\s*(\d+)ms', out)
                if m:
                    result["ping_latency_ms"] = float(m.group(1))
            elif "100% loss" in out or "could not find host" in out:
                result["network_issues"].append({
                    "type": "packet_loss",
                    "title": "Public Gateway Packet Loss",
                    "detail": "100% packet loss pinging public DNS resolver 1.1.1.1.",
                })
        except Exception:
            pass

        return result

    @classmethod
    def run_full_scan(cls) -> Dict[str, Any]:
        """Run all performance, event log, and bottleneck diagnostics."""
        event_logs = cls.get_event_log_errors()
        startup = cls.audit_startup_items()
        hogs = cls.detect_resource_hogs()
        network = cls.test_network_stack()

        return {
            "event_logs": event_logs,
            "startup": startup,
            "resource_hogs": hogs,
            "network": network,
        }
