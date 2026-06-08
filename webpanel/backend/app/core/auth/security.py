from datetime import UTC, datetime, timedelta
import os
import string

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError, VerificationError


JWT_ALGORITHM = "HS256"
DEV_TEST_ENVIRONMENTS = {"dev", "development", "local", "test", "testing"}
DEFAULT_DEV_SECRET_KEY = "dev-only-change-me"
DEFAULT_ACCESS_TOKEN_EXPIRE_MINUTES = 60
MIN_PASSWORD_LENGTH = 12


def get_runtime_environment() -> str:
    return os.getenv("HOSTPILOT_ENV", "development").strip().lower()


def get_access_token_expire_minutes() -> int:
    raw_value = os.getenv("HOSTPILOT_ACCESS_TOKEN_MINUTES", str(DEFAULT_ACCESS_TOKEN_EXPIRE_MINUTES))
    try:
        minutes = int(raw_value)
    except ValueError as exc:
        raise RuntimeError("HOSTPILOT_ACCESS_TOKEN_MINUTES must be an integer.") from exc

    if minutes <= 0:
        raise RuntimeError("HOSTPILOT_ACCESS_TOKEN_MINUTES must be greater than zero.")
    return minutes


def get_secret_key() -> str:
    secret_key = os.getenv("HOSTPILOT_SECRET_KEY")
    if secret_key:
        return secret_key

    if get_runtime_environment() in DEV_TEST_ENVIRONMENTS:
        return DEFAULT_DEV_SECRET_KEY

    raise RuntimeError("HOSTPILOT_SECRET_KEY is required outside development/test environments.")

password_hasher = PasswordHasher(
    time_cost=3,
    memory_cost=65536,
    parallelism=4,
    hash_len=32,
    salt_len=16,
)


def hash_password(password: str) -> str:
    return password_hasher.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    if not password_hash:
        return False
    try:
        return password_hasher.verify(password_hash, password)
    except (VerifyMismatchError, VerificationError):
        return False


def validate_password_policy(password: str) -> list[str]:
    errors: list[str] = []
    if len(password) < MIN_PASSWORD_LENGTH:
        errors.append(f"Password must be at least {MIN_PASSWORD_LENGTH} characters.")
    if not any(character.islower() for character in password):
        errors.append("Password must include a lowercase letter.")
    if not any(character.isupper() for character in password):
        errors.append("Password must include an uppercase letter.")
    if not any(character.isdigit() for character in password):
        errors.append("Password must include a number.")
    if not any(character in string.punctuation for character in password):
        errors.append("Password must include a symbol.")
    return errors


def create_access_token(user_id: int) -> str:
    expires_at = datetime.now(UTC) + timedelta(minutes=get_access_token_expire_minutes())
    payload = {
        "sub": str(user_id),
        "type": "access",
        "exp": expires_at,
        "iat": datetime.now(UTC),
    }
    return jwt.encode(payload, get_secret_key(), algorithm=JWT_ALGORITHM)


def decode_access_token(token: str) -> int | None:
    try:
        payload = jwt.decode(token, get_secret_key(), algorithms=[JWT_ALGORITHM])
    except jwt.PyJWTError:
        return None

    if payload.get("type") != "access":
        return None

    subject = payload.get("sub")
    if subject is None:
        return None

    try:
        return int(subject)
    except ValueError:
        return None
