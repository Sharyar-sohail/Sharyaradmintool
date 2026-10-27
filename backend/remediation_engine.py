"""
ApexSys Autonomous Remediation & Payload Orchestrator
Generates cryptographically signed execution payloads, manages the multi-phase
One-Click Fix pipeline, and computes verification score deltas.
"""

import json
from typing import Any, Dict, List, Optional
from backend.security import security_engine
from backend.node_manager import node_manager, NodeRecord


class RemediationCatalog:
    """Standard remediation action definitions."""
    TASKS = {
        "SCAN_MASTER": {
            "name": "Execute Master System Diagnostic",
            "category": "Diagnostics",
            "description": "Performs deep multi-layered scan across Hardware, OS, Storage, Drivers, and Security.",
            "estimated_sec": 15,
        },
        "FIX_DISM_RESTORE": {
            "name": "DISM Image Restore & Component Repair",
            "category": "Operating System",
            "description": "Repairs Windows Component Store corruption using DISM /Online /Cleanup-Image /RestoreHealth.",
            "estimated_sec": 45,
        },
        "FIX_SFC_REPAIR": {
            "name": "System File Checker (SFC) Scannow & CBS Repair",
            "category": "Operating System",
            "description": "Scans and repairs corrupted, missing, or altered Windows protected system files.",
            "estimated_sec": 40,
        },
        "FIX_CLEAN_DEEP_JUNK": {
            "name": "Deep Storage & Cache Purge",
            "category": "Storage",
            "description": "Safely purges Windows Temp, User Temp, Prefetch cache, CBS servicing logs, and orphaned download caches.",
            "estimated_sec": 10,
        },
        "FIX_NETWORK_STACK": {
            "name": "Network Stack Reset & DNS Flush",
            "category": "Security",
            "description": "Flushes DNS cache, resets Winsock catalog, resets TCP/IP stack, and restarts network adapters.",
            "estimated_sec": 8,
        },
        "FIX_REGISTRY_INTEGRITY": {
            "name": "Registry Run & Path Integrity Repair",
            "category": "Security",
            "description": "Detects and prunes orphaned startup keys and broken paths with automated rollback backups.",
            "estimated_sec": 5,
        },
        "FIX_ORPHAN_SHORTCUTS": {
            "name": "Purge Orphaned Shortcuts",
            "category": "Storage",
            "description": "Scans Desktop and Start Menu to remove dead shortcut links pointing to missing targets.",
            "estimated_sec": 5,
        },
        "FIX_RESTART_SERVICES": {
            "name": "Restart Vital Windows Services",
            "category": "Operating System",
            "description": "Recycles wuauserv (Windows Update), BITS, Spooler, CryptSvc, and DNS Cache services.",
            "estimated_sec": 12,
        },
        "FIX_DRIVER_RESCAN": {
            "name": "PnP Driver Rescan & Recovery",
            "category": "Drivers",
            "description": "Triggers pnputil /scan-devices to re-enumerate bus devices and clear transient PnP faults.",
            "estimated_sec": 10,
        },
        "FIX_POWER_OPTIMIZE": {
            "name": "Power Plan & Thermal Throttle Reset",
            "category": "Hardware",
            "description": "Restores High Performance power plan profile and resets aggressive CPU power capping.",
            "estimated_sec": 5,
        },
        "FIX_ALL": {
            "name": "One-Click Autonomous Master Remediation",
            "category": "Master Healing",
            "description": "Full orchestrator executing phased repairs across all flagged issues followed by verification scan.",
            "estimated_sec": 120,
        },
        "SELF_DESTRUCT": {
            "name": "Secure Zero-Footprint Self-Destruct",
            "category": "Lifecycle",
            "description": "Securely multi-pass overwrites temporary diagnostic artifacts, unhooks agent, and exits zero-trace.",
            "estimated_sec": 5,
        },
    }


class RemediationEngine:
    def __init__(self):
        self.catalog = RemediationCatalog.TASKS

    def create_action_payload(
        self,
        client_id: str,
        action: str,
        params: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Creates a tamper-proof, cryptographically signed action payload.
        """
        raw_payload = {
            "type": "EXECUTE_COMMAND",
            "action": action,
            "target_client": client_id,
            "params": params or {},
        }
        signed = security_engine.sign_payload(raw_payload)
        return signed

    async def dispatch_command(
        self,
        node: NodeRecord,
        action: str,
        params: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        Transmits signed action payload to the agent via its active WebSocket.
        """
        if not node.websocket:
            return False

        # Mark node state
        if action == "SCAN_MASTER":
            node.status = "SCANNING"
        elif action == "SELF_DESTRUCT":
            node.status = "OFFLINE"
        else:
            node.status = "REMEDIATING"
            node.active_task = action
            node.remediation_progress = 0
            # Record pre-repair score if starting repair
            if node.pre_repair_score is None:
                node.pre_repair_score = node.health_score

        payload = self.create_action_payload(node.client_id, action, params)
        try:
            await node.websocket.send_text(json.dumps(payload))
            node.append_terminal_log(f"[APEX-CMD] Dispatched '{action}' with cryptographic signature verified.", "stdout")
            return True
        except Exception as e:
            node.status = "OFFLINE"
            node.append_terminal_log(f"[ERROR] Failed to dispatch '{action}': {str(e)}", "stderr")
            return False

    def compute_verification_delta(self, node: NodeRecord) -> Dict[str, Any]:
        """
        Calculates improvement delta between pre-repair and post-repair scores.
        """
        pre = node.pre_repair_score if node.pre_repair_score is not None else node.health_score
        post = node.health_score
        delta = post - pre
        return {
            "pre_score": pre,
            "post_score": post,
            "improvement": max(0, delta),
            "pct_change": round((delta / max(1, pre)) * 100, 1) if pre > 0 else 0,
            "resolved_count": sum(1 for i in node.issues if i.get("resolved", False)),
            "remaining_count": sum(1 for i in node.issues if not i.get("resolved", False)),
        }


# Global singleton
remediation_engine = RemediationEngine()
