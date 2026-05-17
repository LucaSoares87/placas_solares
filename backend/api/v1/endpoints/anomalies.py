"""
Endpoints de consulta e gestão de anomalias energéticas.
"""

from typing import Annotated

import structlog
from fastapi import APIRouter, Depends, Path, Query
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.v1.dependencies import CurrentUser, EngineeringRequired
from backend.core.database import get_db_session
from backend.repositories.energy_anomaly_repository import EnergyAnomalyRepository
from backend.schemas.common import APIResponse, PaginatedResponse
from backend.schemas.energy_anomaly import EnergyAnomalyResponse
import math

router = APIRouter(prefix="/anomalies", tags=["Anomalias Energéticas"])
logger = structlog.get_logger(__name__)


@router.get(
    "/",
    response_model=PaginatedResponse[EnergyAnomalyResponse],
)
async def list_unresolved_anomalies(
    _: CurrentUser,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
):
    """Lista anomalias não resolvidas, ordenadas por data de detecção."""
    repo = EnergyAnomalyRepository(session)
    offset = (page - 1) * page_size
    items = await repo.list_unresolved(offset, page_size)
    total = await repo.count_all()

    return PaginatedResponse(
        data=[EnergyAnomalyResponse.model_validate(i) for i in items],
        total=total,
        page=page,
        page_size=page_size,
        pages=math.ceil(total / page_size),
    )


@router.get(
    "/transformer/{transformer_id}",
    response_model=PaginatedResponse[EnergyAnomalyResponse],
)
async def list_anomalies_by_transformer(
    transformer_id: str,
    _: CurrentUser,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
):
    repo = EnergyAnomalyRepository(session)
    offset = (page - 1) * page_size
    items = await repo.list_by_transformer(transformer_id, offset, page_size)

    return PaginatedResponse(
        data=[EnergyAnomalyResponse.model_validate(i) for i in items],
        total=len(items),
        page=page,
        page_size=page_size,
        pages=math.ceil(len(items) / page_size) if items else 1,
    )


@router.get(
    "/uc/{uc_code}",
    response_model=PaginatedResponse[EnergyAnomalyResponse],
)
async def list_anomalies_by_uc(
    uc_code: str,
    _: CurrentUser,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
):
    repo = EnergyAnomalyRepository(session)
    offset = (page - 1) * page_size
    items = await repo.list_by_uc(uc_code, offset, page_size)

    return PaginatedResponse(
        data=[EnergyAnomalyResponse.model_validate(i) for i in items],
        total=len(items),
        page=page,
        page_size=page_size,
        pages=math.ceil(len(items) / page_size) if items else 1,
    )


@router.patch(
    "/{anomaly_id}/resolve",
    response_model=APIResponse[EnergyAnomalyResponse],
    dependencies=[EngineeringRequired],
)
async def resolve_anomaly(
    anomaly_id: int = Path(..., ge=1),
    session: Annotated[AsyncSession, Depends(get_db_session)] = None,
):
    """Marca uma anomalia como resolvida."""
    repo = EnergyAnomalyRepository(session)
    anomaly = await repo.resolve(anomaly_id)
    if not anomaly:
        from backend.core.exceptions import EntityNotFoundException
        raise EntityNotFoundException(
            message=f"Anomalia {anomaly_id} não encontrada.",
            details={"id": anomaly_id},
        )
    logger.info("anomaly.resolved", anomaly_id=anomaly_id)
    return APIResponse(
        data=EnergyAnomalyResponse.model_validate(anomaly),
        message="Anomalia marcada como resolvida.",
    )
