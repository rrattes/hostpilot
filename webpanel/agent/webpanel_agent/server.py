from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from typing import Any

from webpanel_agent.actions.mock import run_mock_action
from webpanel_agent.contracts import AgentActionRequest, AgentContractError
from webpanel_agent.policies.allowlist import allowed_actions


DEFAULT_AGENT_HOST = "127.0.0.1"
DEFAULT_AGENT_PORT = 8765


def agent_health() -> dict[str, Any]:
    return {
        "status": "ok",
        "mode": "local-http",
        "bind_host": DEFAULT_AGENT_HOST,
        "allowed_actions": allowed_actions(),
    }


class AgentRequestHandler(BaseHTTPRequestHandler):
    server_version = "HostPilotAgent/0.1"

    def do_GET(self) -> None:
        if self.path != "/health":
            self._write_json(404, {"error": "Not found"})
            return
        self._write_json(200, agent_health())

    def do_POST(self) -> None:
        if self.path != "/actions":
            self._write_json(404, {"error": "Not found"})
            return

        try:
            body = self._read_json_body()
            request = AgentActionRequest.from_dict(body)
        except (AgentContractError, json.JSONDecodeError, ValueError) as exc:
            self._write_json(400, {"error": str(exc)})
            return

        response = run_mock_action(request)
        self._write_json(200, response.to_dict())

    def log_message(self, format: str, *args: object) -> None:
        return

    def _read_json_body(self) -> dict[str, Any]:
        length_header = self.headers.get("Content-Length", "0")
        length = int(length_header)
        raw_body = self.rfile.read(length)
        payload = json.loads(raw_body.decode("utf-8") if raw_body else "{}")
        if not isinstance(payload, dict):
            raise ValueError("Request body must be a JSON object.")
        return payload

    def _write_json(self, status_code: int, payload: dict[str, Any]) -> None:
        encoded = json.dumps(payload).encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)


def create_server(
    host: str = DEFAULT_AGENT_HOST,
    port: int = DEFAULT_AGENT_PORT,
) -> ThreadingHTTPServer:
    if host != DEFAULT_AGENT_HOST:
        raise ValueError("HostPilot agent must bind to 127.0.0.1 only.")
    return ThreadingHTTPServer((host, port), AgentRequestHandler)


def run_server(host: str = DEFAULT_AGENT_HOST, port: int = DEFAULT_AGENT_PORT) -> None:
    server = create_server(host, port)
    try:
        server.serve_forever()
    finally:
        server.server_close()
