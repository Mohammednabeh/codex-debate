import json
import sys
import threading
import unittest
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1] / "scripts"))

import adapters


class _Handler(BaseHTTPRequestHandler):
    def do_POST(self):
        length = int(self.headers["Content-Length"])
        body = json.loads(self.rfile.read(length))
        response = json.dumps({"answer": body["task_packet"]["objective"]}).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(response)))
        self.end_headers()
        self.wfile.write(response)

    def log_message(self, *_args):
        return


class AdapterTests(unittest.TestCase):
    def test_api_adapter_calls_real_http_endpoint_and_normalizes_result(self):
        server = HTTPServer(("127.0.0.1", 0), _Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            provider = {
                "provider_id": "local-api",
                "transport": "api",
                "endpoint": f"http://127.0.0.1:{server.server_port}",
                "credential_env": None,
            }
            packet = {
                "packet_version": 1,
                "task_id": "task-1",
                "role": "coding",
                "objective": "return this objective",
                "relevant_context": [],
                "constraints": [],
                "evidence": [],
                "artifacts": [],
                "required_output": {"format": "json"},
                "acceptance_criteria": [],
                "privacy": "normal",
            }

            result = adapters.ApiAdapter().ask(provider, packet)

            self.assertEqual(result["status"], "success")
            self.assertEqual(result["result"]["answer"], "return this objective")
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=2)

    def test_browser_action_contains_task_packet_and_provider_urls(self):
        provider = {
            "provider_id": "browser-provider",
            "transport": "browser",
            "endpoint": "https://chat.example.com",
            "browser_profile": {"login_url": "https://chat.example.com/login"},
        }
        packet = {"packet_version": 1, "task_id": "task-2", "objective": "answer"}

        action = adapters.prepare_browser_action(provider, packet)

        self.assertEqual(action["action"], "browser_provider_task")
        self.assertEqual(action["provider_url"], "https://chat.example.com")
        self.assertEqual(action["login_url"], "https://chat.example.com/login")
        self.assertEqual(action["task_packet"]["task_id"], "task-2")

    def test_cli_adapter_executes_without_shell_and_normalizes_result(self):
        provider = {
            "provider_id": "local-cli",
            "transport": "cli",
            "command": [
                sys.executable,
                "-c",
                "import json,sys; p=json.load(sys.stdin); print(json.dumps({'answer': p['task_packet']['objective']}))",
            ],
        }
        packet = {
            "packet_version": 1,
            "task_id": "task-cli",
            "role": "coding",
            "objective": "cli objective",
            "relevant_context": [],
            "constraints": [],
            "evidence": [],
            "artifacts": [],
            "required_output": {"format": "json"},
            "acceptance_criteria": [],
            "privacy": "normal",
        }

        result = adapters.CliAdapter().ask(provider, packet)

        self.assertEqual(result["status"], "success")
        self.assertEqual(result["result"]["answer"], "cli objective")

    def test_ready_browser_observation_becomes_result_packet(self):
        observation = {
            "packet_version": 1,
            "provider_id": "browser-provider",
            "state": "READY",
            "page_url": "https://chat.example.com/chat/1",
            "answer": "rendered answer",
            "signals": ["chat_ready", "completed"],
        }
        packet = {"packet_version": 1, "task_id": "task-2", "objective": "answer"}

        result = adapters.consume_browser_observation(observation, packet)

        self.assertEqual(result["status"], "success")
        self.assertEqual(result["result"]["answer"], "rendered answer")
