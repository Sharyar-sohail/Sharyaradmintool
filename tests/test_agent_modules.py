"""
Integration & Unit tests for ApexSys Client Agent Diagnostic Modules
Tests hardware queries, junk calculation, network latency testing, and secure file shredding.
"""

import os
import tempfile
import unittest
from agent.modules.hardware import HardwareDiagnostics
from agent.modules.os_integrity import OSIntegrityDiagnostics
from agent.modules.performance import PerformanceDiagnostics
from agent.self_destruct import SelfDestructProtocol


class TestAgentModules(unittest.TestCase):
    def test_hardware_cpu_query(self):
        cpu = HardwareDiagnostics.get_cpu_and_thermal()
        self.assertIsInstance(cpu, dict)
        self.assertIn("model", cpu)
        self.assertIn("cores", cpu)
        self.assertGreaterEqual(cpu.get("cores", 0), 1)

    def test_pnp_failing_devices_query(self):
        pnp = HardwareDiagnostics.get_failing_pnp_devices()
        self.assertIsInstance(pnp, dict)
        self.assertIn("failing_devices", pnp)
        self.assertIn("failing_count", pnp)

    def test_storage_and_junk_calculation(self):
        storage = OSIntegrityDiagnostics.get_logical_storage_status()
        self.assertIsInstance(storage, dict)
        self.assertGreaterEqual(len(storage.get("drives", [])), 1)

        junk = OSIntegrityDiagnostics.calculate_deep_junk_mb()
        self.assertIsInstance(junk, dict)
        self.assertIn("total_junk_mb", junk)

    def test_network_stack_latency(self):
        net = PerformanceDiagnostics.test_network_stack()
        self.assertIsInstance(net, dict)
        self.assertIn("dns_latency_ms", net)
        self.assertIn("dns_healthy", net)

    def test_secure_shred_protocol(self):
        # Create a temporary file with confidential content
        with tempfile.NamedTemporaryFile(delete=False) as tf:
            tf.write(b"TOP SECRET APEXSYS DIAGNOSTIC CACHE DATA 1234567890")
            temp_path = tf.name

        self.assertTrue(os.path.exists(temp_path))

        # Perform 3-pass DoD overwrite shred
        shred_res = SelfDestructProtocol.secure_shred_file(temp_path, passes=3)
        self.assertTrue(shred_res)
        self.assertFalse(os.path.exists(temp_path), "File should be completely unlinked and erased.")


if __name__ == "__main__":
    unittest.main()
