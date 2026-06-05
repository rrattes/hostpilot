from collections import defaultdict, deque
from datetime import UTC, datetime, timedelta


MAX_LOGIN_ATTEMPTS = 5
LOGIN_WINDOW_SECONDS = 60

_attempts: dict[str, deque[datetime]] = defaultdict(deque)


def is_login_limited(key: str) -> bool:
    now = datetime.now(UTC)
    window_start = now - timedelta(seconds=LOGIN_WINDOW_SECONDS)
    attempts = _attempts[key]

    while attempts and attempts[0] < window_start:
        attempts.popleft()

    return len(attempts) >= MAX_LOGIN_ATTEMPTS


def record_failed_login(key: str) -> None:
    _attempts[key].append(datetime.now(UTC))


def clear_login_attempts(key: str) -> None:
    _attempts.pop(key, None)


def clear_all_login_attempts() -> None:
    _attempts.clear()
