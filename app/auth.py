"""Token handling and permission checks, enforced once at the gateway."""
import os

import jwt
from strawberry.permission import BasePermission
from strawberry.types import Info

SECRET = os.getenv("GATEWAY_JWT_SECRET", "dev-only-secret-change-me-in-production-0123456789")
ALGORITHM = "HS256"


def issue_token(subject: str, permissions: list[str]) -> str:
    """Issue a signed token. In a real system the auth service does this."""
    return jwt.encode({"sub": subject, "permissions": permissions}, SECRET, algorithm=ALGORITHM)


def decode_token(header: str | None) -> dict | None:
    """Return the token claims from an Authorization header, or None if invalid."""
    if not header or not header.startswith("Bearer "):
        return None
    try:
        return jwt.decode(header[7:], SECRET, algorithms=[ALGORITHM])
    except jwt.PyJWTError:
        return None


class HasPermission(BasePermission):
    """Allow a field only if the caller's token carries the given permission code."""

    message = "Permission denied"

    def __init__(self, code: str):
        self.code = code

    def has_permission(self, source, info: Info, **kwargs) -> bool:
        user = info.context.get("user")
        return bool(user and self.code in user.get("permissions", []))
