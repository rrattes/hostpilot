from time import perf_counter
from typing import Any

from app.core.agent_gateway.contracts import AgentActionRequest, AgentActionResponse


ALLOWED_MOCK_ACTIONS = {
    "mock.health",
    "mock.system_info",
    "web.nginx.apply_site_config",
    "web.nginx.disable_site_config",
    "web.logs.tail_site_logs",
}


def allowed_mock_actions() -> list[str]:
    return sorted(ALLOWED_MOCK_ACTIONS)


def run_mock_action(request: AgentActionRequest) -> AgentActionResponse:
    started_at = perf_counter()

    if request.action not in ALLOWED_MOCK_ACTIONS:
        return _response(False, "rejected", {}, "Action is not allowed.", started_at)

    if request.action == "mock.health":
        return _response(True, "completed", {"status": "ok", "mode": "mock"}, None, started_at)

    if request.action == "mock.system_info":
        return _response(
            True,
            "completed",
            {
                "hostname": "hostpilot-local-dev",
                "os": "Ubuntu Server 26.04 LTS",
                "cpu_load_percent": 18,
                "memory_used_percent": 42,
                "disk_used_percent": 37,
            },
            None,
            started_at,
        )

    if request.action == "web.nginx.apply_site_config":
        return _response(
            False,
            "rejected",
            {},
            "Local agent is required for controlled Nginx apply.",
            started_at,
        )

    if request.action == "web.nginx.disable_site_config":
        return _response(
            False,
            "rejected",
            {},
            "Local agent is required for controlled Nginx disable.",
            started_at,
        )

    if request.action == "web.logs.tail_site_logs":
        return _response(
            False,
            "rejected",
            {},
            "Local agent is required for Web site log access.",
            started_at,
        )

    return _response(False, "rejected", {}, "Unknown action.", started_at)


def _response(
    success: bool,
    status: str,
    data: dict[str, Any],
    error: str | None,
    started_at: float,
) -> AgentActionResponse:
    return AgentActionResponse(
        success=success,
        status=status,
        data=data,
        error=error,
        duration_ms=int((perf_counter() - started_at) * 1000),
    )
