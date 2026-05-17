from typing import Annotated

import structlog
from fastapi import Depends, Header
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.database import get_db_session
from backend.core.exceptions import ForbiddenException, UnauthorizedException
from backend.core.security import decode_access_token
from backend.domain.entities import UserProfile
from backend.models.user import AuthorizedUser
from backend.repositories.user_repository import UserRepository

logger = structlog.get_logger(__name__)
_bearer = HTTPBearer(auto_error=False)


async def get_current_user(
    session: Annotated[AsyncSession, Depends(get_db_session)],
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
) -> AuthorizedUser:
    if not credentials:
        raise UnauthorizedException(message="Token de autenticação ausente.")

    payload = decode_access_token(credentials.credentials)
    matricula: str | None = payload.get("sub")

    if not matricula:
        raise UnauthorizedException(message="Token malformado.")

    repo = UserRepository(session)
    user = await repo.get_active_by_matricula(matricula)

    if not user:
        raise UnauthorizedException(message="Usuário não encontrado ou inativo.")

    return user


CurrentUser = Annotated[AuthorizedUser, Depends(get_current_user)]


def require_profiles(*profiles: UserProfile):
    async def _check(current_user: CurrentUser) -> AuthorizedUser:
        if current_user.perfil not in [p.value for p in profiles]:
            raise ForbiddenException(
                message="Permissão insuficiente para esta operação.",
                details={"required": [p.value for p in profiles], "current": current_user.perfil},
            )
        return current_user

    return Depends(_check)


AdminRequired = require_profiles(UserProfile.ADMIN)
EngineeringRequired = require_profiles(UserProfile.ADMIN, UserProfile.ENGINEERING)
FieldRequired = require_profiles(UserProfile.ADMIN, UserProfile.ENGINEERING, UserProfile.FIELD)
