import base64
import hashlib
import hmac
import json
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any

from app.core.config import settings

PASSWORD_ALGORITHM = "pbkdf2_sha256"
PASSWORD_ITERATIONS = 260_000
TOKEN_ALGORITHM = "HS256"


def _base64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _base64url_decode(data: str) -> bytes:
    padding = "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode(data + padding)


def hash_password(password: str) -> str:
    """Hashes a plain-text password using PBKDF2 with a secure random salt.

    Args:
        password: Plain-text password to hash.

    Returns:
        Formatted string containing algorithm parameters, salt, and digest.
    """
    salt = secrets.token_urlsafe(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        PASSWORD_ITERATIONS,
    )
    return f"{PASSWORD_ALGORITHM}${PASSWORD_ITERATIONS}${salt}${_base64url_encode(digest)}"


def verify_password(password: str, password_hash: str) -> bool:
    """Verifies a plain-text password against a PBKDF2 password hash.

    Args:
        password: The plain-text password to verify.
        password_hash: The stored PBKDF2 hash string.

    Returns:
        True if password matches the hash, False otherwise.
    """
    try:
        algorithm, iterations, salt, expected = password_hash.split("$", 3)
        if algorithm != PASSWORD_ALGORITHM:
            return False

        digest = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            salt.encode("utf-8"),
            int(iterations),
        )
        return hmac.compare_digest(_base64url_encode(digest), expected)
    except ValueError:
        return False


def is_password_hash(value: str) -> bool:
    """Checks if a string is formatted as a valid PBKDF2 password hash.

    Args:
        value: String to verify.

    Returns:
        True if formatted as PBKDF2, False otherwise.
    """
    return value.startswith(f"{PASSWORD_ALGORITHM}$")


def create_access_token(subject: str | int, expires_delta: timedelta | None = None) -> str:
    """Generates a signed JWT access token for authentication.

    Args:
        subject: The user identifier (subject) to encode.
        expires_delta: Optional custom duration for the token's lifetime.

    Returns:
        A signed JWT token string.
    """
    expires_at = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    header = {"alg": TOKEN_ALGORITHM, "typ": "JWT"}
    payload = {"sub": str(subject), "exp": int(expires_at.timestamp())}

    signing_input = ".".join(
        [
            _base64url_encode(json.dumps(header, separators=(",", ":")).encode("utf-8")),
            _base64url_encode(json.dumps(payload, separators=(",", ":")).encode("utf-8")),
        ]
    )
    signature = hmac.new(
        settings.SECRET_KEY.encode("utf-8"),
        signing_input.encode("ascii"),
        hashlib.sha256,
    ).digest()
    return f"{signing_input}.{_base64url_encode(signature)}"


def decode_access_token(token: str) -> dict[str, Any] | None:
    """Decodes and validates a signed JWT access token.

    Args:
        token: The signed JWT token string.

    Returns:
        The dictionary payload if valid and unexpired, None otherwise.
    """
    try:
        header_b64, payload_b64, signature_b64 = token.split(".", 2)
        signing_input = f"{header_b64}.{payload_b64}"
        expected_signature = hmac.new(
            settings.SECRET_KEY.encode("utf-8"),
            signing_input.encode("ascii"),
            hashlib.sha256,
        ).digest()
        if not hmac.compare_digest(_base64url_encode(expected_signature), signature_b64):
            return None

        header = json.loads(_base64url_decode(header_b64))
        if header.get("alg") != TOKEN_ALGORITHM:
            return None

        payload = json.loads(_base64url_decode(payload_b64))
        if int(payload.get("exp", 0)) < int(datetime.now(timezone.utc).timestamp()):
            return None

        return payload
    except (ValueError, json.JSONDecodeError, TypeError):
        return None
