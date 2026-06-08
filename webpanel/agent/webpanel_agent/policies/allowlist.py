ALLOWED_ACTIONS = {"mock.health", "mock.system_info"}


def allowed_actions() -> list[str]:
    return sorted(ALLOWED_ACTIONS)


def is_action_allowed(action: str) -> bool:
    return action in ALLOWED_ACTIONS
