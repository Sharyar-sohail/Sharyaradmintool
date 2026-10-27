import os
import shutil
import unittest
from dashboard.fetcher import (
    fetch_isolated_status,
    fetch_isolated_commands,
    send_isolated_command,
    get_customized_agent_script,
)

class TestStateFetcher(unittest.TestCase):
    def setUp(self):
        self.test_token = "APEX-TEST-UNIT"
        self.repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.test_client_dir = os.path.join(self.repo_root, "clients", self.test_token)

    def tearDown(self):
        if os.path.exists(self.test_client_dir):
            shutil.rmtree(self.test_client_dir, ignore_errors=True)

    def test_fetch_demo_status(self):
        status, src = fetch_isolated_status("APEX-DEMO01")
        self.assertIsNotNone(status)
        self.assertEqual(status.get("agent_token"), "APEX-DEMO01")
        self.assertTrue(status.get("health_score") > 0)

    def test_fetch_nonexistent_token(self):
        status, src = fetch_isolated_status("APEX-NONEXISTENT-99999")
        self.assertIsNone(status)

    def test_send_and_fetch_isolated_command(self):
        ok, msg = send_isolated_command(
            agent_token=self.test_token,
            action="CLEAN_ALL_JUNK",
            parameters={"test_mode": True},
        )
        self.assertTrue(ok)
        self.assertIn("CLEAN_ALL_JUNK", msg)

        # Fetch commands
        cmd_data, src = fetch_isolated_commands(self.test_token)
        self.assertIsNotNone(cmd_data)
        self.assertEqual(cmd_data.get("action"), "CLEAN_ALL_JUNK")
        self.assertEqual(cmd_data.get("status"), "PENDING")
        self.assertEqual(cmd_data.get("agent_token"), self.test_token)

    def test_get_customized_agent_script(self):
        script = get_customized_agent_script("APEX-CUSTOM123", "TestOwner", "TestRepo", "main")
        self.assertIn('AgentToken = "APEX-CUSTOM123"', script)
        self.assertIn('RepoOwner = "TestOwner"', script)
        self.assertIn('RepoName = "TestRepo"', script)

if __name__ == "__main__":
    unittest.main()
