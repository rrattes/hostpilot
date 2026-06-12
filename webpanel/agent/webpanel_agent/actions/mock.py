from time import perf_counter
from typing import Any

from webpanel_agent.actions.nginx import apply_site_config, disable_site_config, tail_site_logs
from webpanel_agent.contracts import AgentActionRequest, AgentActionResponse
from webpanel_agent.mock.system_info import get_mock_system_info
from webpanel_agent.policies.allowlist import is_action_allowed


def run_mock_action(request: AgentActionRequest) -> AgentActionResponse:
    started_at = perf_counter()

    if not is_action_allowed(request.action):
        return _response(False, "rejected", {}, "Action is not allowed.", started_at)

    if request.action == "mock.health":
        return _response(True, "completed", {"status": "ok", "mode": "mock"}, None, started_at)

    if request.action == "mock.system_info":
        return _response(True, "completed", dict(get_mock_system_info()), None, started_at)

    if request.action == "web.nginx.apply_site_config":
        try:
            result = apply_site_config(request.payload)
        except ValueError as exc:
            return _response(False, "rejected", {}, str(exc), started_at)
        return _response(
            bool(result.get("applied")),
            str(result.get("status", "failed")),
            result,
            None if result.get("applied") else str(result.get("status", "Apply failed.")),
            started_at,
        )

    if request.action == "web.nginx.disable_site_config":
        try:
            result = disable_site_config(request.payload)
        except ValueError as exc:
            return _response(False, "rejected", {}, str(exc), started_at)
        return _response(
            bool(result.get("disabled")),
            str(result.get("status", "failed")),
            result,
            None if result.get("disabled") else str(result.get("status", "Disable failed.")),
            started_at,
        )

    if request.action == "web.logs.tail_site_logs":
        try:
            result = tail_site_logs(request.payload)
        except ValueError as exc:
            return _response(False, "rejected", {}, str(exc), started_at)
        return _response(True, str(result.get("status", "completed")), result, None, started_at)

    return _response(False, "rejected", {}, "Unknown action.", started_at)


def _response(
    success: bool,
    status: str,
    data: dict[str, Any],
    error: str | None,
    started_at: float,
) -> AgentActionResponse:
    duration_ms = int((perf_counter() - started_at) * 1000)
    return AgentActionResponse(
        success=success,
        status=status,
        data=data,
        error=error,
        duration_ms=duration_ms,
    )
