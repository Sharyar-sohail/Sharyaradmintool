"""
ApexSys Node Manager & Telemetry Hub
Tracks connected machines, stores real-time telemetry buffers, computes holistic
health scores, categorizes diagnostic issues, and manages WebSocket channels.
"""

import time
from typing import Any, Dict, List, Optional
from fastapi import WebSocket


class NodeRecord:
    def __init__(self, client_id: str, websocket: Optional[WebSocket] = None):
        self.client_id = client_id
        self.websocket = websocket
        self.status = "ONLINE"  # ONLINE, SCANNING, REMEDIATING, OFFLINE
        self.last_seen = time.time()
        self.connected_at = time.time()

        # System Specs
        self.system_info: Dict[str, Any] = {
            "hostname": client_id,
            "os_name": "Unknown",
            "os_version": "Unknown",
            "os_build": "Unknown",
            "architecture": "x64",
            "cpu_model": "Unknown",
            "cpu_cores": 0,
            "total_ram_gb": 0.0,
            "is_admin": False,
            "ip_address": "127.0.0.1",
            "mac_address": "Unknown",
        }

        # Rolling Telemetry Buffer (last 30 data points)
        self.telemetry_history: List[Dict[str, Any]] = []

        # Diagnostic Data & Issues
        self.health_score: int = 100
        self.category_scores: Dict[str, int] = {
            "Hardware": 100,
            "Operating System": 100,
            "Storage": 100,
            "Drivers": 100,
            "Security": 100,
        }
        self.issues: List[Dict[str, Any]] = []
        self.raw_diagnostics: Dict[str, Any] = {}

        # Remediation Task State
        self.active_task: Optional[str] = None
        self.remediation_progress: int = 0
        self.terminal_logs: List[Dict[str, Any]] = []  # {"ts": ..., "stream": "stdout"/"stderr", "text": ...}
        self.pre_repair_score: Optional[int] = None
        self.post_repair_score: Optional[int] = None

    def update_telemetry(self, data: Dict[str, Any]):
        """Record a live telemetry tick."""
        self.last_seen = time.time()
        tick = {
            "timestamp": time.time(),
            "cpu_percent": data.get("cpu_percent", 0.0),
            "ram_percent": data.get("ram_percent", 0.0),
            "ram_used_gb": data.get("ram_used_gb", 0.0),
            "disk_percent": data.get("disk_percent", 0.0),
            "net_latency_ms": data.get("net_latency_ms", 0.0),
            "cpu_freq_mhz": data.get("cpu_freq_mhz", 0.0),
        }
        self.telemetry_history.append(tick)
        if len(self.telemetry_history) > 60:
            self.telemetry_history.pop(0)

    def append_terminal_log(self, text: str, stream: str = "stdout"):
        """Store terminal log lines streamed from agent."""
        log_entry = {
            "ts": time.strftime("%H:%M:%S"),
            "stream": stream,
            "text": text,
        }
        self.terminal_logs.append(log_entry)
        if len(self.terminal_logs) > 500:
            self.terminal_logs.pop(0)

    def process_diagnostics(self, report: Dict[str, Any]):
        """
        Ingest the Master Scan report, compute scores, and extract actionable issues.
        """
        self.raw_diagnostics = report
        self.issues = []

        hw = report.get("hardware", {})
        os_int = report.get("os_integrity", {})
        storage = report.get("storage", {})
        drivers = report.get("drivers", {})
        security = report.get("security", {})
        perf = report.get("performance", {})

        hw_score = 100
        os_score = 100
        storage_score = 100
        drivers_score = 100
        security_score = 100

        # --- 1. HARDWARE EVALUATION ---
        smart_failures = hw.get("smart_failures", [])
        if smart_failures:
            hw_score -= 40 * len(smart_failures)
            for fail in smart_failures:
                self.issues.append({
                    "id": f"hw_smart_{fail.get('drive_id', 'disk')}",
                    "category": "Hardware",
                    "severity": "CRITICAL",
                    "title": f"Critical SMART Disk Failure: {fail.get('model', 'Drive')}",
                    "description": f"Drive {fail.get('device_id', '')} reported predict-failure status. Bad sectors detected: {fail.get('bad_sectors', 0)}.",
                    "fix_id": "FIX_HARDWARE_ALERT",
                    "resolved": False,
                })

        cpu_throttled = hw.get("cpu_throttled", False)
        if cpu_throttled:
            hw_score -= 15
            self.issues.append({
                "id": "hw_cpu_throttle",
                "category": "Hardware",
                "severity": "WARNING",
                "title": "CPU Thermal/Power Throttling Detected",
                "description": f"Processor current clock speed is restricted ({hw.get('cpu_curr_mhz', 0)} MHz vs {hw.get('cpu_max_mhz', 0)} MHz max). Power plan or thermal headroom constrained.",
                "fix_id": "FIX_POWER_OPTIMIZE",
                "resolved": False,
            })

        ram_errors = hw.get("ram_health_issues", [])
        if ram_errors:
            hw_score -= 30
            self.issues.append({
                "id": "hw_ram_anomaly",
                "category": "Hardware",
                "severity": "CRITICAL",
                "title": "Physical RAM Hardware Warning",
                "description": f"RAM anomalies reported: {', '.join(ram_errors)}",
                "fix_id": "FIX_MEMORY_DIAG",
                "resolved": False,
            })

        # --- 2. OS & FILE SYSTEM INTEGRITY ---
        dism_corrupted = os_int.get("dism_corrupted", False)
        if dism_corrupted:
            os_score -= 35
            self.issues.append({
                "id": "os_dism_corruption",
                "category": "Operating System",
                "severity": "CRITICAL",
                "title": "Windows Component Store (DISM) Corruption",
                "description": "Windows system image has corrupted payload packages. Repairable via DISM RestoreHealth.",
                "fix_id": "FIX_DISM_RESTORE",
                "resolved": False,
            })

        sfc_corrupted = os_int.get("sfc_corrupted", False)
        if sfc_corrupted:
            os_score -= 30
            self.issues.append({
                "id": "os_sfc_corruption",
                "category": "Operating System",
                "severity": "CRITICAL",
                "title": "System File Checker (SFC) Integrity Violations",
                "description": f"Damaged protected Windows system binaries found: {os_int.get('corrupted_files_count', 0)} file(s) mismatched hashes.",
                "fix_id": "FIX_SFC_REPAIR",
                "resolved": False,
            })

        cbs_errors = os_int.get("cbs_error_count", 0)
        if cbs_errors > 5 and not sfc_corrupted:
            os_score -= 15
            self.issues.append({
                "id": "os_cbs_errors",
                "category": "Operating System",
                "severity": "WARNING",
                "title": f"Component-Based Servicing (CBS) Log Errors ({cbs_errors} entries)",
                "description": "Servicing engine encountered repetitive packaging errors during recent updates.",
                "fix_id": "FIX_SFC_REPAIR",
                "resolved": False,
            })

        # --- 3. STORAGE EVALUATION ---
        disk_full_drives = storage.get("low_space_drives", [])
        for drv in disk_full_drives:
            storage_score -= 25
            self.issues.append({
                "id": f"storage_full_{drv['letter']}",
                "category": "Storage",
                "severity": "CRITICAL" if drv.get("free_pct", 100) < 5 else "WARNING",
                "title": f"Low Disk Capacity: Drive {drv['letter']} ({drv.get('free_gb', 0):.1f} GB / {drv.get('free_pct', 0):.1f}% Free)",
                "description": "Drive capacity is dangerously low. May cause OS update failures and paging stalls.",
                "fix_id": "FIX_CLEAN_DEEP_JUNK",
                "resolved": False,
            })

        temp_junk_mb = storage.get("temp_junk_mb", 0)
        if temp_junk_mb > 2000:  # > 2GB
            storage_score -= 15
            self.issues.append({
                "id": "storage_junk_accumulated",
                "category": "Storage",
                "severity": "WARNING",
                "title": f"Deep Junk Cache Accumulation: {temp_junk_mb / 1024:.2f} GB",
                "description": "Orphaned Windows update download caches, crash minidumps, Prefetch bloat, and temp files.",
                "fix_id": "FIX_CLEAN_DEEP_JUNK",
                "resolved": False,
            })

        broken_shortcuts = storage.get("broken_shortcuts_count", 0)
        if broken_shortcuts > 3:
            storage_score -= 10
            self.issues.append({
                "id": "storage_broken_shortcuts",
                "category": "Storage",
                "severity": "INFO",
                "title": f"Orphaned Desktop/StartMenu Shortcuts ({broken_shortcuts} items)",
                "description": "Shortcuts pointing to non-existent executable binaries or deleted program paths.",
                "fix_id": "FIX_ORPHAN_SHORTCUTS",
                "resolved": False,
            })

        # --- 4. DRIVERS & HARDWARE INTEGRITY ---
        yellow_bangs = drivers.get("failing_devices", [])
        if yellow_bangs:
            drivers_score -= min(50, len(yellow_bangs) * 20)
            for dev in yellow_bangs:
                self.issues.append({
                    "id": f"driver_pnp_{dev.get('device_id', 'dev')[:16]}",
                    "category": "Drivers",
                    "severity": "CRITICAL" if dev.get("code") in [10, 43] else "WARNING",
                    "title": f"Driver Fault ({dev.get('name', 'PnP Device')}): Code {dev.get('code')}",
                    "description": f"{dev.get('error_desc', 'Hardware device manager error')}. Status: {dev.get('status', 'Error')}.",
                    "fix_id": "FIX_DRIVER_RESCAN",
                    "resolved": False,
                })

        # --- 5. SECURITY & STABILITY ---
        corrupt_reg = security.get("corrupt_registry_keys", [])
        if corrupt_reg:
            security_score -= min(30, len(corrupt_reg) * 10)
            self.issues.append({
                "id": "sec_corrupt_registry",
                "category": "Security",
                "severity": "WARNING",
                "title": f"Damaged Registry Run/Service Keys ({len(corrupt_reg)} entries)",
                "description": "Invalid or orphaned startup registration keys pointing to missing binaries.",
                "fix_id": "FIX_REGISTRY_INTEGRITY",
                "resolved": False,
            })

        bsod_count = perf.get("bsod_events_count", 0)
        if bsod_count > 0:
            security_score -= min(40, bsod_count * 20)
            self.issues.append({
                "id": "sec_bsod_crashes",
                "category": "Security",
                "severity": "CRITICAL",
                "title": f"Recent System Blue Screen (BSOD) Crashes ({bsod_count} events)",
                "description": f"Kernel-Power ID 41 / BugCheck crashes detected in event logs. Latest bugcheck code: {perf.get('latest_bsod_code', 'Unknown')}.",
                "fix_id": "FIX_STABILITY_STACK",
                "resolved": False,
            })

        resource_hogs = perf.get("resource_hogs", [])
        if resource_hogs:
            security_score -= 15
            for hog in resource_hogs:
                self.issues.append({
                    "id": f"perf_hog_{hog['pid']}",
                    "category": "Security",
                    "severity": "WARNING",
                    "title": f"Runaway Process: {hog['name']} (PID {hog['pid']})",
                    "description": f"Consuming excessive resources: CPU {hog.get('cpu_pct', 0):.1f}%, RAM {hog.get('ram_mb', 0):.0f} MB.",
                    "fix_id": f"FIX_KILL_PROCESS_{hog['pid']}",
                    "resolved": False,
                })

        network_issues = perf.get("network_issues", [])
        if network_issues:
            security_score -= 15
            for net_err in network_issues:
                self.issues.append({
                    "id": f"perf_net_{net_err.get('type', 'stack')}",
                    "category": "Security",
                    "severity": "WARNING",
                    "title": f"Network Stack Anomaly: {net_err.get('title', 'DNS/Socket Issue')}",
                    "description": net_err.get("detail", "High latency, DNS failures, or packet drop."),
                    "fix_id": "FIX_NETWORK_STACK",
                    "resolved": False,
                })

        # Clamp category scores
        self.category_scores["Hardware"] = max(0, min(100, hw_score))
        self.category_scores["Operating System"] = max(0, min(100, os_score))
        self.category_scores["Storage"] = max(0, min(100, storage_score))
        self.category_scores["Drivers"] = max(0, min(100, drivers_score))
        self.category_scores["Security"] = max(0, min(100, security_score))

        # Overall weighted composite score
        overall = (
            self.category_scores["Hardware"] * 0.20 +
            self.category_scores["Operating System"] * 0.25 +
            self.category_scores["Storage"] * 0.15 +
            self.category_scores["Drivers"] * 0.20 +
            self.category_scores["Security"] * 0.20
        )
        self.health_score = int(round(overall))

    def to_summary(self) -> Dict[str, Any]:
        """Compact node status for fleet overview."""
        latest_telemetry = self.telemetry_history[-1] if self.telemetry_history else {}
        return {
            "client_id": self.client_id,
            "status": self.status,
            "health_score": self.health_score,
            "category_scores": self.category_scores,
            "issue_counts": {
                "total": len(self.issues),
                "critical": sum(1 for i in self.issues if i["severity"] == "CRITICAL" and not i["resolved"]),
                "warning": sum(1 for i in self.issues if i["severity"] == "WARNING" and not i["resolved"]),
                "info": sum(1 for i in self.issues if i["severity"] == "INFO" and not i["resolved"]),
            },
            "system_info": self.system_info,
            "latest_telemetry": latest_telemetry,
            "active_task": self.active_task,
            "remediation_progress": self.remediation_progress,
            "last_seen_sec_ago": int(time.time() - self.last_seen),
        }

    def to_detail(self) -> Dict[str, Any]:
        """Full node details including raw diagnostic logs and issue list."""
        summary = self.to_summary()
        summary["issues"] = self.issues
        summary["telemetry_history"] = self.telemetry_history
        summary["terminal_logs"] = self.terminal_logs[-100:]
        summary["raw_diagnostics"] = self.raw_diagnostics
        summary["pre_repair_score"] = self.pre_repair_score
        summary["post_repair_score"] = self.post_repair_score
        return summary


class NodeManager:
    def __init__(self):
        self._nodes: Dict[str, NodeRecord] = {}

    def get_or_create(self, client_id: str, websocket: Optional[WebSocket] = None) -> NodeRecord:
        if client_id not in self._nodes:
            self._nodes[client_id] = NodeRecord(client_id, websocket)
        else:
            if websocket:
                self._nodes[client_id].websocket = websocket
                self._nodes[client_id].status = "ONLINE"
                self._nodes[client_id].last_seen = time.time()
        return self._nodes[client_id]

    def get(self, client_id: str) -> Optional[NodeRecord]:
        return self._nodes.get(client_id)

    def list_nodes(self) -> List[Dict[str, Any]]:
        self.check_heartbeats()
        return [node.to_summary() for node in self._nodes.values()]

    def check_heartbeats(self, timeout_sec: float = 30.0):
        now = time.time()
        for node in self._nodes.values():
            if now - node.last_seen > timeout_sec and node.status != "OFFLINE":
                node.status = "OFFLINE"

    def remove_node(self, client_id: str):
        if client_id in self._nodes:
            del self._nodes[client_id]


# Global singleton instance
node_manager = NodeManager()
