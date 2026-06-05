from dataclasses import dataclass
from typing import Literal


RiskLevel = Literal["low", "medium", "high", "critical"]


@dataclass(frozen=True)
class ConfirmationRequirement:
    action: str
    required_phrase: str | None
    risk_level: RiskLevel
    message: str


def confirmation_required(
    *,
    action: str,
    message: str,
    risk_level: RiskLevel = "medium",
    required_phrase: str | None = None,
) -> ConfirmationRequirement:
    return ConfirmationRequirement(
        action=action,
        required_phrase=required_phrase,
        risk_level=risk_level,
        message=message,
    )


def is_confirmation_valid(requirement: ConfirmationRequirement, phrase: str | None = None) -> bool:
    if requirement.required_phrase is None:
        return True
    return phrase == requirement.required_phrase
