from dataclasses import dataclass
from typing import Any


class AgentContractError(ValueError):
    """Raised when an agent payload does not match the transport contract."""


@dataclass(frozen=True)
class AgentActionRequest:
    action: str
    payload: dict[str, Any]
    requested_by: str
    request_id: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "action": self.action,
            "payload": self.payload,
            "requested_by": self.requested_by,
            "request_id": self.request_id,
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "AgentActionRequest":
        action = payload.get("action")
        request_payload = payload.get("payload")
        requested_by = payload.get("requested_by")
        request_id = payload.get("request_id")
        if not isinstance(action, str) or not action:
            raise AgentContractError("Agent action must be a non-empty string.")
        if not isinstance(request_payload, dict):
            raise AgentContractError("Agent payload must be an object.")
        if not isinstance(requested_by, str) or not requested_by:
            raise AgentContractError("Agent requested_by must be a non-empty string.")
        if not isinstance(request_id, str) or not request_id:
            raise AgentContractError("Agent request_id must be a non-empty string.")
        return cls(
            action=action,
            payload=request_payload,
            requested_by=requested_by,
            request_id=request_id,
        )


@dataclass(frozen=True)
class AgentActionResponse:
    success: bool
    status: str
    data: dict[str, Any]
    error: str | None
    duration_ms: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "success": self.success,
            "status": self.status,
            "data": self.data,
            "error": self.error,
            "duration_ms": self.duration_ms,
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "AgentActionResponse":
        success = payload.get("success")
        status = payload.get("status")
        data = payload.get("data")
        error = payload.get("error")
        duration_ms = payload.get("duration_ms")
        if not isinstance(success, bool):
            raise AgentContractError("Agent response success must be a boolean.")
        if not isinstance(status, str) or not status:
            raise AgentContractError("Agent response status must be a non-empty string.")
        if not isinstance(data, dict):
            raise AgentContractError("Agent response data must be an object.")
        if error is not None and not isinstance(error, str):
            raise AgentContractError("Agent response error must be null or a string.")
        if not isinstance(duration_ms, int) or duration_ms < 0:
            raise AgentContractError("Agent response duration_ms must be a non-negative integer.")
        return cls(
            success=success,
            status=status,
            data=data,
            error=error,
            duration_ms=duration_ms,
        )
