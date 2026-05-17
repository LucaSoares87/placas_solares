from datetime import datetime, timedelta, timezone
from typing import Any

from jose import JWTError, jwt

from backend.core.config import get_settings
from backend.core.exceptions import UnauthorizedException

settings = get_settings()

ALGORITHM = settings.jwt_algorithm


def create_access_token(subject: str, extra_claims: dict[str, Any] | None = None) -> str:
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=settings.jwt_access_token_expire_minutes
    )
    payload: dict[str, Any] = {
        "sub": subject,
        "exp": expire,
        "iat": datetime.now(timezone.utc),
        "type": "access",
    }
    if extra_claims:
        payload.update(extra_claims)

    return jwt.encode(payload, settings.jwt_secret_key, algorithm=ALGORITHM)


def decode_access_token(token: str) -> dict[str, Any]:
    try:
        payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[ALGORITHM])
        if payload.get("type") != "access":
            raise UnauthorizedException(message="Token inválido.")
        return payload
    except JWTError:
        raise UnauthorizedException(message="Token inválido ou expirado.")
