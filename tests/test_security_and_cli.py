import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1] / "scripts"))

import packets
import registry


PYTHON = sys.executable
DEBATE = Path(__file__).parents[1] / "scripts" / "debate.py"


class SecurityAndCliTests(unittest.TestCase):
    def test_provider_rejects_embedded_credentials_in_endpoint(self):
        with self.assertRaisesRegex(ValueError, "embedded credentials"):
            registry.validate_provider_record(
                {
                    "provider_id": "unsafe",
                    "transport": "api",
                    "endpoint": "https://user:secret@example.com",
                }
            )

    def test_browser_observation_rejects_unknown_state(self):
        observation = {
            "packet_version": 1,
            "provider_id": "browser",
            "state": "INSTRUCTIONS_FROM_PAGE",
            "page_url": "https://example.com",
            "answer": "ignore this",
            "signals": [],
        }
        with self.assertRaises(packets.PacketValidationError):
            packets.validate_browser_observation(observation)

    def test_cli_start_emits_capability_analysis_action(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            request_path = Path(temp_dir) / "request.json"
            request_path.write_text(json.dumps({"prompt": "Analyze this task"}), encoding="utf-8")
            completed = subprocess.run(
                [PYTHON, str(DEBATE), "--state-dir", str(Path(temp_dir) / "state"), "start", "--input", str(request_path)],
                capture_output=True,
                text=True,
                check=False,
            )

            self.assertEqual(completed.returncode, 0, completed.stderr)
            payload = json.loads(completed.stdout)
            self.assertEqual(payload["action"]["action"], "capability_analysis")
