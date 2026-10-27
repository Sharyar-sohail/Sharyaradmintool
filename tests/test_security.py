"""
Unit tests for ApexSys Security Engine
Tests HMAC signature generation, tamper detection, replay prevention, and expiration.
"""

import time
import unittest
from backend.security import SecurityEngine


class TestSecurityEngine(unittest.TestCase):
    def setUp(self):
        self.sec = SecurityEngine("test-secret-key-12345")

    def test_sign_and_verify_valid(self):
        payload = {"action": "SCAN_MASTER", "target": "PC-TEST-01"}
        signed = self.sec.sign_payload(payload)

        self.assertIn("_signature", signed)
        self.assertIn("_meta", signed)

        is_valid, msg = self.sec.verify_payload(signed)
        self.assertTrue(is_valid, f"Expected valid payload, got: {msg}")

    def test_tamper_detection(self):
        payload = {"action": "SCAN_MASTER", "target": "PC-TEST-01"}
        signed = self.sec.sign_payload(payload)

        # Tamper with action
        signed["action"] = "SELF_DESTRUCT"

        is_valid, msg = self.sec.verify_payload(signed)
        self.assertFalse(is_valid)
        self.assertIn("mismatch", msg.lower())

    def test_replay_attack_prevention(self):
        payload = {"action": "FIX_ALL", "target": "PC-TEST-01"}
        signed = self.sec.sign_payload(payload)

        # First verification should succeed
        is_valid1, _ = self.sec.verify_payload(signed)
        self.assertTrue(is_valid1)

        # Second verification with exact same nonce should fail as replay
        is_valid2, msg = self.sec.verify_payload(signed)
        self.assertFalse(is_valid2)
        self.assertIn("replay", msg.lower())

    def test_timestamp_expiration(self):
        payload = {"action": "FIX_DISM_RESTORE", "target": "PC-TEST-01"}
        signed = self.sec.sign_payload(payload)

        # Forge an expired timestamp
        signed["_meta"]["timestamp"] = int(time.time()) - 400
        # Re-verify should detect skew/expiration
        is_valid, msg = self.sec.verify_payload(signed)
        self.assertFalse(is_valid)
        self.assertIn("expired", msg.lower())


if __name__ == "__main__":
    unittest.main()
