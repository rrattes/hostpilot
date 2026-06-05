ALLOWED_ACTIONS = {"mock.health", "mock.system_info"}


def is_action_allowed(action: str) -> bool:
    return action in ALLOWED_ACTIONS
