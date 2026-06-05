from webpanel_agent.main import health_check
from webpanel_agent.contracts import AgentActionRequest
from webpanel_agent.actions.mock import run_mock_action
from webpanel_agent.mock.system_info import get_mock_system_info


def test_health_check() -> None:
    assert health_check() == {"status": "ok", "mode": "mock"}


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
