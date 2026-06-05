from webpanel_agent.contracts import AgentActionRequest
from webpanel_agent.actions.mock import run_mock_action
from webpanel_agent.mock.system_info import get_mock_system_info


def health_check() -> dict[str, str]:
    return {"status": "ok", "mode": "mock"}


def main() -> None:
    request = AgentActionRequest(
        action="mock.health",
        payload={},
        requested_by="local-dev",
        request_id="local-dev",
    )
    print(
        {
            "health": health_check(),
            "action": run_mock_action(request),
            "system": get_mock_system_info(),
        }
    )


if __name__ == "__main__":
    main()
