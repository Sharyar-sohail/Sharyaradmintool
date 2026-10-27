"""
ApexSys Unified Client Agent
Autonomous Master IT Doctor executing deep hardware diagnostics, OS self-healing,
real-time telemetry streaming, and cryptographic command execution.
"""

import asyncio
import ctypes
import json
import os
import platform
import socket
import sys
import threading
import time
import uuid
from typing import Any, Dict, Optional
import psutil
import websockets

# Import diagnostic modules
from agent.modules.hardware import HardwareDiagnostics
from agent.modules.os_integrity import OSIntegrityDiagnostics
from agent.modules.performance import PerformanceDiagnostics
from agent.modules.remediator import RemediationEngine
from agent.self_destruct import SelfDestructProtocol
from backend.security import SecurityEngine, DEFAULT_SECRET_KEY


class ApexAgent:
    def __init__(
        self,
        server_url: str = "ws://127.0.0.1:8000",
        client_id: Optional[str] = None,
        secret_key: str = DEFAULT_SECRET_KEY,
    ):
        self.server_url = server_url.rstrip("/")
        self.client_id = client_id or f"{platform.node()}-{uuid.uuid4().hex[:6]}"
        self.security = SecurityEngine(secret_key)
        self.ws: Optional[websockets.WebSocketClientProtocol] = None
        self.is_running = True
        self.loop: Optional[asyncio.AbstractEventLoop] = None

        # System info cache
        self.system_info = self._gather_system_info()

    def _is_admin(self) -> bool:
        try:
            return ctypes.windll.shell32.IsUserAnAdmin() != 0
        except Exception:
            return False

    def _gather_system_info(self) -> Dict[str, Any]:
        """Collect static host specifications."""
        try:
            ip = socket.gethostbyname(socket.gethostname())
        except Exception:
            ip = "127.0.0.1"

        total_ram = round(psutil.virtual_memory().total / (1024 ** 3), 1)
        cpu_model = "Unknown"
        try:
            import winreg
            k = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"HARDWARE\DESCRIPTION\System\CentralProcessor\0")
            cpu_model, _ = winreg.QueryValueEx(k, "ProcessorNameString")
        except Exception:
            cpu_model = platform.processor()

        return {
            "hostname": platform.node(),
            "os_name": "Windows",
            "os_version": platform.version(),
            "os_release": platform.release(),
            "architecture": platform.architecture()[0],
            "cpu_model": cpu_model.strip(),
            "cpu_cores": psutil.cpu_count(logical=True),
            "total_ram_gb": total_ram,
            "is_admin": self._is_admin(),
            "ip_address": ip,
            "python_version": platform.python_version(),
        }

    async def send_json(self, payload: Dict[str, Any]):
        """Transmit message over active WebSocket connection."""
        if self.ws:
            try:
                await self.ws.send(json.dumps(payload))
            except Exception:
                pass

    def emit_log(self, text: str, stream: str = "stdout"):
        """Asynchronously stream terminal logs to server."""
        if self.loop and self.ws:
            msg = {
                "type": "TERMINAL_LOG",
                "client_id": self.client_id,
                "stream": stream,
                "text": text,
            }
            asyncio.run_coroutine_threadsafe(self.send_json(msg), self.loop)

    def emit_progress(self, pct: int, action: str):
        """Asynchronously stream progress updates."""
        if self.loop and self.ws:
            msg = {
                "type": "REMEDIATION_PROGRESS",
                "client_id": self.client_id,
                "progress": pct,
                "action": action,
            }
            asyncio.run_coroutine_threadsafe(self.send_json(msg), self.loop)

    async def telemetry_loop(self):
        """Streams real-time CPU, RAM, Disk, and Network stats to the server."""
        while self.is_running:
            try:
                cpu_p = psutil.cpu_percent(interval=None)
                vm = psutil.virtual_memory()
                ram_p = vm.percent
                ram_used_gb = round((vm.total - vm.available) / (1024 ** 3), 2)

                # Primary disk
                disk_p = 0.0
                try:
                    disk_p = psutil.disk_usage("C:\\").percent
                except Exception:
                    pass

                # CPU frequency
                cpu_freq = 0.0
                try:
                    f = psutil.cpu_freq()
                    if f:
                        cpu_freq = round(f.current, 0)
                except Exception:
                    pass

                telemetry = {
                    "type": "TELEMETRY",
                    "client_id": self.client_id,
                    "data": {
                        "cpu_percent": cpu_p,
                        "ram_percent": ram_p,
                        "ram_used_gb": ram_used_gb,
                        "disk_percent": disk_p,
                        "net_latency_ms": 12.0,  # updated via perf
                        "cpu_freq_mhz": cpu_freq,
                    }
                }
                await self.send_json(telemetry)
            except Exception:
                pass
            await asyncio.sleep(2.0)

    def execute_master_scan(self) -> Dict[str, Any]:
        """Runs the exhaustive, multi-layered Master Scan."""
        self.emit_log("[MASTER-SCAN] >>> Initiating comprehensive multi-layer system diagnostic...", "stdout")

        self.emit_log("[1/5] Querying Physical Drive SMART status, NVMe/SSD wear & PnP devices...", "stdout")
        hw_data = HardwareDiagnostics.run_full_scan()

        self.emit_log("[2/5] Inspecting Windows Component Store (DISM) & System File Checker (SFC)...", "stdout")
        os_data = OSIntegrityDiagnostics.run_full_scan()

        self.emit_log("[3/5] Auditing Windows Event Logs for BSODs, Crash Dumps & Disk errors...", "stdout")
        perf_data = PerformanceDiagnostics.run_full_scan()

        report = {
            "hardware": {
                "smart_failures": hw_data.get("smart_failures", []),
                "smart_drives": hw_data.get("smart_drives", []),
                "cpu_throttled": hw_data.get("cpu_throttled", False),
                "cpu_curr_mhz": hw_data.get("cpu_curr_mhz", 0),
                "cpu_max_mhz": hw_data.get("cpu_max_mhz", 0),
                "ram_health_issues": hw_data.get("ram_health_issues", []),
                "ram_modules": hw_data.get("ram_modules", []),
            },
            "os_integrity": {
                "dism_corrupted": os_data.get("dism", {}).get("dism_corrupted", False),
                "dism_status": os_data.get("dism", {}).get("dism_status", "Healthy"),
                "sfc_corrupted": os_data.get("sfc", {}).get("sfc_corrupted", False),
                "corrupted_files_count": os_data.get("sfc", {}).get("corrupted_files_count", 0),
                "cbs_error_count": os_data.get("sfc", {}).get("cbs_error_count", 0),
            },
            "storage": {
                "low_space_drives": os_data.get("storage_metrics", {}).get("low_space_drives", []),
                "temp_junk_mb": os_data.get("junk_metrics", {}).get("total_junk_mb", 0),
                "broken_shortcuts_count": len(os_data.get("broken_shortcuts", [])),
                "broken_shortcuts": os_data.get("broken_shortcuts", []),
            },
            "drivers": {
                "failing_devices": hw_data.get("failing_devices", []),
            },
            "security": {
                "corrupt_registry_keys": os_data.get("broken_registry_keys", []),
            },
            "performance": {
                "bsod_events_count": perf_data.get("event_logs", {}).get("bsod_events_count", 0),
                "latest_bsod_code": perf_data.get("event_logs", {}).get("latest_bsod_code"),
                "critical_errors_count": perf_data.get("event_logs", {}).get("critical_errors_count", 0),
                "resource_hogs": perf_data.get("resource_hogs", []),
                "network_issues": perf_data.get("network", {}).get("network_issues", []),
                "recent_events": perf_data.get("event_logs", {}).get("recent_events", []),
            },
        }

        self.emit_log("[MASTER-SCAN] >>> Diagnostic complete. Aggregated report transmitted to server.", "stdout")
        return report

    def handle_remediation_task(self, action: str, params: Dict[str, Any]):
        """Executes targeted or full remediation in worker thread."""
        try:
            if action == "FIX_ALL":
                RemediationEngine.run_one_click_fix_all(
                    log_cb=self.emit_log,
                    progress_cb=self.emit_progress,
                )
            elif action == "FIX_DISM_RESTORE":
                RemediationEngine.run_dism_restore(log_cb=self.emit_log, progress_cb=self.emit_progress)
            elif action == "FIX_SFC_REPAIR":
                RemediationEngine.run_sfc_repair(log_cb=self.emit_log, progress_cb=self.emit_progress)
            elif action == "FIX_CLEAN_DEEP_JUNK":
                RemediationEngine.clean_deep_junk(log_cb=self.emit_log, progress_cb=self.emit_progress)
            elif action == "FIX_NETWORK_STACK":
                RemediationEngine.run_network_reset(log_cb=self.emit_log, progress_cb=self.emit_progress)
            elif action == "FIX_REGISTRY_INTEGRITY":
                RemediationEngine.fix_registry_integrity(log_cb=self.emit_log, progress_cb=self.emit_progress)
            elif action == "FIX_ORPHAN_SHORTCUTS":
                RemediationEngine.prune_broken_shortcuts(log_cb=self.emit_log, progress_cb=self.emit_progress)
            elif action == "FIX_RESTART_SERVICES":
                RemediationEngine.restart_vital_services(log_cb=self.emit_log, progress_cb=self.emit_progress)
            elif action == "FIX_DRIVER_RESCAN":
                RemediationEngine.rescan_pnp_drivers(log_cb=self.emit_log, progress_cb=self.emit_progress)
            elif action == "FIX_POWER_OPTIMIZE":
                RemediationEngine.optimize_power(log_cb=self.emit_log, progress_cb=self.emit_progress)
            elif action.startswith("FIX_KILL_PROCESS"):
                pid = params.get("pid")
                if not pid and "_" in action:
                    try:
                        pid = int(action.split("_")[-1])
                    except Exception:
                        pass
                if pid:
                    RemediationEngine.kill_process(pid, log_cb=self.emit_log, progress_cb=self.emit_progress)

            # Verification scan after any fix
            self.emit_log("[VERIFY] Re-running diagnostics for resolution verification...", "stdout")
            report = self.execute_master_scan()

            if self.loop and self.ws:
                msg = {
                    "type": "VERIFICATION_COMPLETE",
                    "client_id": self.client_id,
                    "action": action,
                    "report": report,
                }
                asyncio.run_coroutine_threadsafe(self.send_json(msg), self.loop)

        except Exception as e:
            self.emit_log(f"[FATAL REMEDIATION ERROR] {str(e)}", "stderr")

    async def handle_message(self, raw_msg: str):
        """Process incoming command payloads from the server."""
        try:
            data = json.loads(raw_msg)
        except Exception:
            return

        msg_type = data.get("type")
        if msg_type == "EXECUTE_COMMAND":
            # Cryptographic verification
            is_valid, reason = self.security.verify_payload(data)
            if not is_valid:
                self.emit_log(f"[SECURITY ALERT] Rejected unauthorized command: {reason}", "stderr")
                return

            action = data.get("action")
            params = data.get("params", {})
            self.emit_log(f"[APEX-CMD] Cryptographic token verified. Executing '{action}'...", "stdout")

            if action == "SCAN_MASTER":
                # Run scan in thread
                threading.Thread(target=self._run_and_send_scan, daemon=True).start()

            elif action == "SELF_DESTRUCT":
                self.emit_log("[SELF-DESTRUCT] Initiating secure wipe & zero-trace exit...", "stdout")
                await self.send_json({"type": "SELF_DESTRUCT_INITIATED", "client_id": self.client_id})
                SelfDestructProtocol.execute_cleanup(destroy_self=False)
                self.is_running = False
                if self.ws:
                    await self.ws.close()
                sys.exit(0)

            else:
                # Remediation action
                threading.Thread(
                    target=self.handle_remediation_task,
                    args=(action, params),
                    daemon=True,
                ).start()

    def _run_and_send_scan(self):
        report = self.execute_master_scan()
        if self.loop and self.ws:
            msg = {
                "type": "DIAGNOSTIC_REPORT",
                "client_id": self.client_id,
                "data": report,
            }
            asyncio.run_coroutine_threadsafe(self.send_json(msg), self.loop)

    async def run(self):
        """Main agent WebSocket connection loop with auto-reconnect."""
        self.loop = asyncio.get_running_loop()
        ws_endpoint = f"{self.server_url}/ws/agent/{self.client_id}"

        while self.is_running:
            try:
                print(f"[ApexAgent] Connecting to Commander at {ws_endpoint}...")
                async with websockets.connect(ws_endpoint) as websocket:
                    self.ws = websocket
                    print(f"[ApexAgent] Connected successfully. Client ID: {self.client_id}")

                    # Handshake: transmit system specs
                    handshake = {
                        "type": "HANDSHAKE",
                        "client_id": self.client_id,
                        "system_info": self.system_info,
                    }
                    await self.send_json(handshake)

                    # Trigger initial scan
                    threading.Thread(target=self._run_and_send_scan, daemon=True).start()

                    # Start telemetry streamer
                    telemetry_task = asyncio.create_task(self.telemetry_loop())

                    # Listen for commands
                    async for message in websocket:
                        await self.handle_message(message)

                    telemetry_task.cancel()

            except (websockets.ConnectionClosed, ConnectionRefusedError, OSError) as e:
                print(f"[ApexAgent] Connection lost or unavailable: {e}. Retrying in 4s...")
                await asyncio.sleep(4.0)
            except Exception as e:
                print(f"[ApexAgent] Unexpected error: {e}. Retrying in 4s...")
                await asyncio.sleep(4.0)


def start_agent_standalone(server_url: str = "ws://127.0.0.1:8000", client_id: Optional[str] = None):
    agent = ApexAgent(server_url=server_url, client_id=client_id)
    try:
        asyncio.run(agent.run())
    except KeyboardInterrupt:
        print("[ApexAgent] Interrupted by user.")


if __name__ == "__main__":
    url = sys.argv[1] if len(sys.argv) > 1 else "ws://127.0.0.1:8000"
    cid = sys.argv[2] if len(sys.argv) > 2 else None
    start_agent_standalone(server_url=url, client_id=cid)
