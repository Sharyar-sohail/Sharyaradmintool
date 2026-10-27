"""
Unit tests for ApexSys Node Manager & Health Score Engine
Tests telemetry ingestion, holistic scoring across 5 categories, and issue generation.
"""

import unittest
from backend.node_manager import NodeRecord, NodeManager


class TestNodeManager(unittest.TestCase):
    def setUp(self):
        self.mgr = NodeManager()

    def test_node_creation_and_telemetry(self):
        node = self.mgr.get_or_create("CLIENT-TEST-01")
        self.assertEqual(node.client_id, "CLIENT-TEST-01")
        self.assertEqual(node.status, "ONLINE")

        node.update_telemetry({
            "cpu_percent": 35.5,
            "ram_percent": 62.0,
            "disk_percent": 45.0,
            "net_latency_ms": 15.0,
        })

        self.assertEqual(len(node.telemetry_history), 1)
        self.assertEqual(node.telemetry_history[0]["cpu_percent"], 35.5)

    def test_holistic_health_scoring_clean(self):
        node = self.mgr.get_or_create("CLIENT-CLEAN")
        clean_report = {
            "hardware": {"smart_failures": [], "cpu_throttled": False, "ram_health_issues": []},
            "os_integrity": {"dism_corrupted": False, "sfc_corrupted": False, "cbs_error_count": 0},
            "storage": {"low_space_drives": [], "temp_junk_mb": 200, "broken_shortcuts_count": 0},
            "drivers": {"failing_devices": []},
            "security": {"corrupt_registry_keys": []},
            "performance": {"bsod_events_count": 0, "resource_hogs": [], "network_issues": []},
        }
        node.process_diagnostics(clean_report)
        self.assertEqual(node.health_score, 100)
        self.assertEqual(len(node.issues), 0)

    def test_holistic_health_scoring_with_issues(self):
        node = self.mgr.get_or_create("CLIENT-FAULTY")
        faulty_report = {
            "hardware": {
                "smart_failures": [{"drive_id": "0", "model": "Kingston", "bad_sectors": 12}],
                "cpu_throttled": True,
                "ram_health_issues": [],
            },
            "os_integrity": {
                "dism_corrupted": True,
                "sfc_corrupted": True,
                "corrupted_files_count": 4,
                "cbs_error_count": 15,
            },
            "storage": {
                "low_space_drives": [{"letter": "C", "free_pct": 3.0, "free_gb": 4.2}],
                "temp_junk_mb": 8500,
                "broken_shortcuts_count": 5,
            },
            "drivers": {
                "failing_devices": [{"name": "SAS Controller", "code": 28, "status": "Error"}],
            },
            "security": {
                "corrupt_registry_keys": [{"name": "OldApp"}],
            },
            "performance": {
                "bsod_events_count": 2,
                "latest_bsod_code": "Kernel-Power 41",
                "resource_hogs": [{"pid": 9999, "name": "bad_miner.exe", "cpu_pct": 98.0, "ram_mb": 2000}],
                "network_issues": [{"type": "packet_loss", "title": "Loss"}],
            },
        }
        node.process_diagnostics(faulty_report)

        # Health score must be significantly penalized
        self.assertLess(node.health_score, 60)
        self.assertGreater(len(node.issues), 5)

        # Categories must be penalized
        self.assertLess(node.category_scores["Hardware"], 60)
        self.assertLess(node.category_scores["Operating System"], 50)
        self.assertLess(node.category_scores["Storage"], 70)


if __name__ == "__main__":
    unittest.main()
