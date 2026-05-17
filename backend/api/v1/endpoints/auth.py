from typing import Annotated

import structlog
from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.database import get_db_session
from backend.core.security import create_access_token
from backend.repositories.access_log_repository import AccessLogRepository
from backend.schemas.common import APIResponse
from backend.schemas.user import LoginRequest, TokenResponse, UserReadPublic
from backend.services.user_service import UserService

router = APIRouter(prefix="/auth", tags=["Autenticação"])
logger = structlog.get_logger(__name__)


@router.post("/login", response_model=APIResponse[TokenResponse])
async def login(
    body: LoginRequest,
    request: Request,
    session: Annotated[AsyncSession, Depends(get_db_session)],
):
    service = UserService(session)
    log_repo = AccessLogRepository(session)
    ip = request.client.host if request.client else None
    ua = request.headers.get("user-agent")

    user = await service.authenticate(body.matricula, body.password)

    token = create_access_token(
        subject=user.matricula,
        extra_claims={"perfil": user.perfil},
    )

    await log_repo.create_log(
        action="login",
        user_id=user.id,
        matricula=user.matricula,
        ip_address=ip,
        user_agent=ua,
        success=True,
    )

    logger.info("auth.login.success", matricula=user.matricula)

    return APIResponse(
        data=TokenResponse(
            access_token=token,
            expires_in=480 * 60,
            user=UserReadPublic.model_validate(user),
        )
    )
