from typing import Annotated

import structlog
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.v1.dependencies import CurrentUser, EngineeringRequired
from backend.core.database import get_db_session
from backend.schemas.common import APIResponse, PaginatedResponse, PaginationParams
from backend.schemas.consumer_unit import (
    ConsumerUnitCreate,
    ConsumerUnitRead,
    ConsumerUnitUpdate,
)
from backend.services.consumer_unit_service import ConsumerUnitService

router = APIRouter(prefix="/consumer-units", tags=["Unidades Consumidoras"])
logger = structlog.get_logger(__name__)


@router.post(
    "",
    response_model=APIResponse[ConsumerUnitRead],
    dependencies=[EngineeringRequired],
)
async def create_consumer_unit(
    body: ConsumerUnitCreate,
    session: Annotated[AsyncSession, Depends(get_db_session)],
):
    service = ConsumerUnitService(session)
    uc = await service.create(body)
    return APIResponse(data=ConsumerUnitRead.model_validate(uc), message="UC criada com sucesso.")


@router.get("/{uc_code}", response_model=APIResponse[ConsumerUnitRead])
async def get_consumer_unit(
    uc_code: str,
    _: CurrentUser,
    session: Annotated[AsyncSession, Depends(get_db_session)],
):
    service = ConsumerUnitService(session)
    uc = await service.get_by_uc_code(uc_code)
    return APIResponse(data=ConsumerUnitRead.model_validate(uc))


@router.get("", response_model=PaginatedResponse[ConsumerUnitRead])
async def list_consumer_units(
    _: CurrentUser,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
):
    params = PaginationParams(page=page, page_size=page_size)
    service = ConsumerUnitService(session)
    items, total = await service.list_paginated(params.offset, params.page_size)
    pages = -(-total // params.page_size)
    return PaginatedResponse(
        data=[ConsumerUnitRead.model_validate(u) for u in items],
        total=total,
        page=params.page,
        page_size=params.page_size,
        pages=pages,
    )


@router.get(
    "/transformer/{transformer_id}",
    response_model=PaginatedResponse[ConsumerUnitRead],
)
async def list_by_transformer(
    transformer_id: str,
    _: CurrentUser,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=100, ge=1, le=500),
):
    params = PaginationParams(page=page, page_size=page_size)
    service = ConsumerUnitService(session)
    items, total = await service.list_by_transformer(
        transformer_id, params.offset, params.page_size
    )
    pages = -(-total // params.page_size)
    return PaginatedResponse(
        data=[ConsumerUnitRead.model_validate(u) for u in items],
        total=total,
        page=params.page,
        page_size=params.page_size,
        pages=pages,
    )


@router.patch(
    "/{uc_code}",
    response_model=APIResponse[ConsumerUnitRead],
    dependencies=[EngineeringRequired],
)
async def update_consumer_unit(
    uc_code: str,
    body: ConsumerUnitUpdate,
    session: Annotated[AsyncSession, Depends(get_db_session)],
):
    service = ConsumerUnitService(session)
    uc = await service.update(uc_code, body)
    return APIResponse(data=ConsumerUnitRead.model_validate(uc))


@router.delete(
    "/{uc_code}",
    response_model=APIResponse[None],
    dependencies=[EngineeringRequired],
)
async def delete_consumer_unit(
    uc_code: str,
    session: Annotated[AsyncSession, Depends(get_db_session)],
):
    service = ConsumerUnitService(session)
    await service.delete(uc_code)
    return APIResponse(message=f"UC {uc_code} removida.")
