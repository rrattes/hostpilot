import os
from typing import Any

import httpx

from app.core.agent_gateway.contracts import (
    AgentActionRequest,
    AgentActionResponse,
    AgentContractError,
)


DEFAULT_AGENT_URL = "http://127.0.0.1:8765"
DEFAULT_AGENT_TIMEOUT_SECONDS = 2.0


class LocalAgentTransportError(RuntimeError):
    pass


def get_agent_url() -> str:
    return os.getenv("HOSTPILOT_AGENT_URL", DEFAULT_AGENT_URL).rstrip("/")


def get_agent_timeout_seconds() -> float:
    raw_value = os.getenv("HOSTPILOT_AGENT_TIMEOUT_SECONDS", str(DEFAULT_AGENT_TIMEOUT_SECONDS))
    try:
        timeout = float(raw_value)
    except ValueError as exc:
        raise RuntimeError("HOSTPILOT_AGENT_TIMEOUT_SECONDS must be numeric.") from exc
    if timeout <= 0:
        raise RuntimeError("HOSTPILOT_AGENT_TIMEOUT_SECONDS must be greater than zero.")
    return timeout


def get_local_agent_health() -> dict[str, Any]:
    try:
        response = httpx.get(f"{get_agent_url()}/health", timeout=get_agent_timeout_seconds())
        response.raise_for_status()
        payload = response.json()
    except (httpx.HTTPError, ValueError) as exc:
        raise LocalAgentTransportError(str(exc)) from exc

    if not isinstance(payload, dict):
        raise LocalAgentTransportError("Agent health response must be an object.")
    return payload


def execute_local_agent_action(request: AgentActionRequest) -> AgentActionResponse:
    try:
        response = httpx.post(
            f"{get_agent_url()}/actions",
            json=request.to_dict(),
            timeout=get_agent_timeout_seconds(),
        )
        response.raise_for_status()
        payload = response.json()
    except (httpx.HTTPError, ValueError) as exc:
        raise LocalAgentTransportError(str(exc)) from exc

    if not isinstance(payload, dict):
        raise LocalAgentTransportError("Agent action response must be an object.")
    try:
        return AgentActionResponse.from_dict(payload)
    except AgentContractError as exc:
        raise LocalAgentTransportError(str(exc)) from exc
