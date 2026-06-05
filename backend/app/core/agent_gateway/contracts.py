from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class AgentActionRequest:
    action: str
    payload: dict[str, Any]
    requested_by: str
    request_id: str


@dataclass(frozen=True)
class AgentActionResponse:
    success: bool
    status: str
    data: dict[str, Any]
    error: str | None
    duration_ms: int
