from typing import Annotated

import structlog
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.v1.dependencies import AdminRequired, CurrentUser
from backend.core.database import get_db_session
from backend.schemas.common import APIResponse, PaginatedResponse, PaginationParams
from backend.schemas.user import UserCreate, UserRead, UserReadPublic, UserUpdate
from backend.services.user_service import UserService

router = APIRouter(prefix="/users", tags=["Usuários"])
logger = structlog.get_logger(__name__)


@router.post("", response_model=APIResponse[UserRead], dependencies=[AdminRequired])
async def create_user(
    body: UserCreate,
    session: Annotated[AsyncSession, Depends(get_db_session)],
):
    service = UserService(session)
    user = await service.create(body)
    return APIResponse(data=UserRead.model_validate(user), message="Usuário criado com sucesso.")


@router.get("/me", response_model=APIResponse[UserReadPublic])
async def get_me(current_user: CurrentUser):
    return APIResponse(data=UserReadPublic.model_validate(current_user))


@router.get("", response_model=PaginatedResponse[UserRead], dependencies=[AdminRequired])
async def list_users(
    session: Annotated[AsyncSession, Depends(get_db_session)],
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
):
    params = PaginationParams(page=page, page_size=page_size)
    service = UserService(session)
    items, total = await service.list_paginated(params.offset, params.page_size)
    pages = -(-total // params.page_size)
    return PaginatedResponse(
        data=[UserRead.model_validate(u) for u in items],
        total=total,
        page=params.page,
        page_size=params.page_size,
        pages=pages,
    )


@router.patch("/{matricula}", response_model=APIResponse[UserRead], dependencies=[AdminRequired])
async def update_user(
    matricula: str,
    body: UserUpdate,
    session: Annotated[AsyncSession, Depends(get_db_session)],
):
    service = UserService(session)
    user = await service.update(matricula, body)
    return APIResponse(data=UserRead.model_validate(user))


@router.delete("/{matricula}", response_model=APIResponse[None], dependencies=[AdminRequired])
async def deactivate_user(
    matricula: str,
    session: Annotated[AsyncSession, Depends(get_db_session)],
):
    service = UserService(session)
    await service.deactivate(matricula)
    return APIResponse(message=f"Usuário {matricula} desativado.")
