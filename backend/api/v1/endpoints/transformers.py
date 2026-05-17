from typing import Annotated

import structlog
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.v1.dependencies import CurrentUser, EngineeringRequired
from backend.core.database import get_db_session
from backend.schemas.common import APIResponse, PaginatedResponse, PaginationParams
from backend.schemas.transformer import TransformerCreate, TransformerRead
from backend.services.transformer_service import TransformerService

router = APIRouter(prefix="/transformers", tags=["Transformadores"])
logger = structlog.get_logger(__name__)


@router.post(
    "",
    response_model=APIResponse[TransformerRead],
    dependencies=[EngineeringRequired],
)
async def create_transformer(
    body: TransformerCreate,
    session: Annotated[AsyncSession, Depends(get_db_session)],
):
    service = TransformerService(session)
    transformer = await service.create(body)
    return APIResponse(
        data=TransformerRead.model_validate(transformer),
        message="Transformador criado com sucesso.",
    )


@router.get("/{transformer_id}", response_model=APIResponse[TransformerRead])
async def get_transformer(
    transformer_id: str,
    _: CurrentUser,
    session: Annotated[AsyncSession, Depends(get_db_session)],
):
    service = TransformerService(session)
    transformer = await service.get_by_id(transformer_id)
    return APIResponse(data=TransformerRead.model_validate(transformer))


@router.get("", response_model=PaginatedResponse[TransformerRead])
async def list_transformers(
    _: CurrentUser,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    substation: str | None = Query(default=None),
):
    params = PaginationParams(page=page, page_size=page_size)
    service = TransformerService(session)

    if substation:
        items = await service.list_by_substation(substation, params.offset, params.page_size)
        total = len(items)
    else:
        items, total = await service.list_paginated(params.offset, params.page_size)

    pages = -(-total // params.page_size) if total > 0 else 1
    return PaginatedResponse(
        data=[TransformerRead.model_validate(t) for t in items],
        total=total,
        page=params.page,
        page_size=params.page_size,
        pages=pages,
    )


@router.delete(
    "/{transformer_id}",
    response_model=APIResponse[None],
    dependencies=[EngineeringRequired],
)
async def delete_transformer(
    transformer_id: str,
    session: Annotated[AsyncSession, Depends(get_db_session)],
):
    service = TransformerService(session)
    await service.delete(transformer_id)
    return APIResponse(message=f"Transformador {transformer_id} removido.")
