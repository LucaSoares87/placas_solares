"""
Endpoints do módulo climático.

Rotas:
  POST /climate/transformer          → dados climáticos por transformador
  GET  /climate/correction-factor    → fator de correção para balanço
  POST /climate/async                → coleta assíncrona via Celery
  POST /climate/async/all            → coleta para todos os transformadores
"""

from __future__ import annotations

from datetime import date
from typing import Annotated

import structlog
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.v1.dependencies import CurrentUser, EngineeringRequired
from backend.core.database import get_db_session
from backend.core.exceptions import EntityNotFoundException, ValidationException
from backend.core.redis import get_redis_client
from backend.schemas.climate import (
    ClimateCorrectionResponse,
    TransformerClimateRequest,
    TransformerClimateResponse,
)
from backend.schemas.common import APIResponse
from backend.services.climate_service import ClimateService

router = APIRouter(prefix="/climate", tags=["Clima"])
logger = structlog.get_logger(__name__)


@router.post(
    "/transformer",
    response_model=APIResponse[TransformerClimateResponse],
    summary="Dados Climáticos por Transformador",
    description=(
        "Busca dados climáticos históricos para o transformador informado. "
        "Estratégia de fonte: INMET → NASA POWER → PVGIS. "
        "Resultado é cacheado no Redis e persistido no banco."
    ),
)
async def fetch_transformer_climate(
    body: TransformerClimateRequest,
    _: CurrentUser,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> APIResponse[TransformerClimateResponse]:
    if body.date_start > body.date_end:
        raise ValidationException(
            message="date_start deve ser anterior ou igual a date_end.",
            details={},
        )

    redis = await get_redis_client()
    service = ClimateService(session, redis)

    try:
        result = await service.fetch_for_transformer(
            transformer_id=body.transformer_id,
            date_start=body.date_start,
            date_end=body.date_end,
            force_refresh=body.force_refresh,
        )
    except ValueError as exc:
        raise EntityNotFoundException(
            message=str(exc),
            details={"transformer_id": body.transformer_id},
        )

    logger.info(
        "api.climate.transformer_fetched",
        transformer_id=body.transformer_id,
        total_days=result.total_days,
        source=result.source,
    )
    return APIResponse(
        data=result,
        message=f"{result.total_days} dias coletados via {result.source}.",
    )


@router.get(
    "/correction-factor",
    response_model=APIResponse[ClimateCorrectionResponse],
    summary="Fator de Correção Climática",
    description=(
        "Retorna o fator de correção climática composto para um transformador "
        "em uma data de referência. Usado pelo balanço energético."
    ),
)
async def get_correction_factor(
    _: CurrentUser,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    transformer_id: str = Query(..., min_length=2, max_length=30),
    ref_date: date = Query(..., description="YYYY-MM-DD"),
) -> APIResponse[ClimateCorrectionResponse]:
    redis = await get_redis_client()
    service = ClimateService(session, redis)

    location = await service._repo.get_transformer_location(transformer_id)
    if not location:
        raise EntityNotFoundException(
            message=f"Transformador '{transformer_id}' sem coordenadas.",
            details={"transformer_id": transformer_id},
        )

    correction = await service.get_correction_factor(
        transformer_id=transformer_id,
        latitude=location[0],
        longitude=location[1],
        ref_date=ref_date,
    )
    if not correction:
        raise EntityNotFoundException(
            message=f"Dados climáticos não encontrados para {transformer_id} em {ref_date}.",
            details={"transformer_id": transformer_id, "ref_date": str(ref_date)},
        )

    return APIResponse(
        data=correction,
        message=f"Fator composto: {correction.composite_factor:.4f}",
    )


@router.post(
    "/async",
    summary="Coleta Assíncrona para um Transformador",
    description="Envia coleta de dados climáticos para a fila Celery.",
    dependencies=[EngineeringRequired],
)
async def trigger_async_climate(
    body: TransformerClimateRequest,
) -> APIResponse[dict]:
    from backend.workers.tasks.climate_tasks import task_fetch_transformer_climate

    task = task_fetch_transformer_climate.delay(
        transformer_id=body.transformer_id,
        date_start_iso=str(body.date_start),
        date_end_iso=str(body.date_end),
        force_refresh=body.force_refresh,
    )

    logger.info(
        "api.climate.async_triggered",
        transformer_id=body.transformer_id,
        task_id=task.id,
    )
    return APIResponse(
        data={"task_id": task.id, "status": "queued"},
        message="Coleta climática enviada para a fila.",
    )


@router.post(
    "/async/all",
    summary="Coleta Assíncrona para Todos os Transformadores",
    description="Dispara coleta climática em lote via Celery para todos os transformadores.",
    dependencies=[EngineeringRequired],
)
async def trigger_async_climate_all(
    date_start: date = Query(...),
    date_end: date = Query(...),
    force_refresh: bool = Query(default=False),
) -> APIResponse[dict]:
    from backend.workers.tasks.climate_tasks import task_fetch_all_climate

    task = task_fetch_all_climate.delay(
        date_start_iso=str(date_start),
        date_end_iso=str(date_end),
        force_refresh=force_refresh,
    )

    return APIResponse(
        data={"task_id": task.id, "status": "queued"},
        message="Coleta em lote enviada para a fila.",
    )
