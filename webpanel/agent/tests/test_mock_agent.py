import json
from threading import Thread
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from webpanel_agent.main import health_check
from webpanel_agent.contracts import AgentActionRequest, AgentContractError
from webpanel_agent.actions.mock import run_mock_action
from webpanel_agent.mock.system_info import get_mock_system_info
from webpanel_agent.server import create_server


def test_health_check() -> None:
    assert health_check()["status"] == "ok"
    assert health_check()["mode"] == "local-http"
    assert health_check()["allowed_actions"] == [
        "mock.health",
        "mock.system_info",
        "web.logs.tail_site_logs",
        "web.nginx.apply_site_config",
        "web.nginx.disable_site_config",
    ]


def test_mock_system_info() -> None:
    system_info = get_mock_system_info()

    assert system_info["hostname"] == "hostpilot-local-dev"
    assert system_info["os"] == "Ubuntu Server 26.04 LTS"


def test_unknown_action_rejected() -> None:
    response = run_mock_action(
        AgentActionRequest(
            action="real.system",
            payload={},
            requested_by="test",
            request_id="req-1",
        )
    )

    assert response.success is False
    assert response.status == "rejected"


def test_contract_rejects_invalid_request() -> None:
    try:
        AgentActionRequest.from_dict({"action": "mock.health", "payload": {}})
    except AgentContractError as exc:
        assert "requested_by" in str(exc)
    else:
        raise AssertionError("Invalid request should be rejected")


def test_local_http_agent_health_and_action() -> None:
    server = create_server(port=0)
    host, port = server.server_address
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        with urlopen(f"http://{host}:{port}/health", timeout=2) as response:
            health = json.loads(response.read().decode("utf-8"))

        request = Request(
            f"http://{host}:{port}/actions",
            data=json.dumps(
                {
                    "action": "mock.health",
                    "payload": {},
                    "requested_by": "test",
                    "request_id": "req-1",
                }
            ).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urlopen(request, timeout=2) as response:
            action_response = json.loads(response.read().decode("utf-8"))
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)

    assert health["mode"] == "local-http"
    assert action_response["success"] is True
    assert action_response["data"]["status"] == "ok"


def test_local_http_agent_rejects_bad_contract() -> None:
    server = create_server(port=0)
    host, port = server.server_address
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        request = Request(
            f"http://{host}:{port}/actions",
            data=json.dumps({"action": "mock.health", "payload": {}}).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            urlopen(request, timeout=2)
        except HTTPError as exc:
            status_code = exc.code
            error_payload = json.loads(exc.read().decode("utf-8"))
        else:
            raise AssertionError("Invalid contract should return HTTP 400")
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)

    assert status_code == 400
    assert "requested_by" in error_payload["error"]
