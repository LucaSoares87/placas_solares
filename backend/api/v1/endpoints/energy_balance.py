"""
Endpoints de Balanço Energético.

Rotas:
  POST /transformer-balance          → calcular balanço individual
  POST /transformer-balance/batch    → calcular em lote
  POST /transformer-balance/all      → calcular para todos
  GET  /transformer-balance/summary  → sumário analítico do período
  POST /transformer-balance/async    → disparar task assíncrona (Celery)
"""

from __future__ import annotations

from datetime import datetime
from typing import Annotated

import structlog
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.v1.dependencies import CurrentUser, EngineeringRequired
from backend.core.database import get_db_session
from backend.core.exceptions import EntityNotFoundException, ValidationException
from backend.schemas.common import APIResponse
from backend.schemas.energy_balance import (
    BalanceComputeRequest,
    BalanceComputeResponse,
    BalanceSummaryResponse,
    BatchBalanceRequest,
    BatchBalanceResponse,
)
from backend.services.energy_balance_service import EnergyBalanceService

router = APIRouter(prefix="/transformer-balance", tags=["Balanço Energético"])
logger = structlog.get_logger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# Cálculo individual
# ─────────────────────────────────────────────────────────────────────────────

@router.post(
    "",
    response_model=APIResponse[BalanceComputeResponse],
    summary="Calcular Balanço de um Transformador",
    description=(
        "Calcula o balanço energético de um transformador para o período informado. "
        "Agrega as inferências das UCs, aplica perdas técnicas e classifica o resultado."
    ),
    dependencies=[EngineeringRequired],
)
async def compute_transformer_balance(
    body: BalanceComputeRequest,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> APIResponse[BalanceComputeResponse]:
    if body.period_start >= body.period_end:
        raise ValidationException(
            message="period_start deve ser anterior a period_end.",
            details={"period_start": str(body.period_start), "period_end": str(body.period_end)},
        )

    service = EnergyBalanceService(session)
    try:
        result = await service.compute_transformer_balance(
            transformer_id=body.transformer_id,
            period_start=body.period_start,
            period_end=body.period_end,
            force_recalculate=body.force_recalculate,
        )
    except ValueError as exc:
        raise EntityNotFoundException(
            message=str(exc),
            details={"transformer_id": body.transformer_id},
        )

    logger.info(
        "api.balance.computed",
        transformer_id=body.transformer_id,
        status=result.balance_status,
        pct_error=result.percentage_error,
    )
    return APIResponse(
        data=result,
        message=f"Balanço calculado: {result.balance_status} ({result.percentage_error:.2f}%)",
    )


# ─────────────────────────────────────────────────────────────────────────────
# Cálculo em lote
# ─────────────────────────────────────────────────────────────────────────────

@router.post(
    "/batch",
    response_model=APIResponse[BatchBalanceResponse],
    summary="Calcular Balanço em Lote",
    description="Calcula balanço energético para múltiplos transformadores em uma única requisição.",
    dependencies=[EngineeringRequired],
)
async def compute_batch_balance(
    body: BatchBalanceRequest,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> APIResponse[BatchBalanceResponse]:
    if body.period_start >= body.period_end:
        raise ValidationException(
            message="period_start deve ser anterior a period_end.",
            details={},
        )

    service = EnergyBalanceService(session)
    result = await service.compute_batch_balance(
        transformer_ids=body.transformer_ids,
        period_start=body.period_start,
        period_end=body.period_end,
        force_recalculate=body.force_recalculate,
    )

    logger.info(
        "api.balance.batch_computed",
        total_computed=result.total_computed,
        total_failed=result.total_failed,
    )
    return APIResponse(
        data=result,
        message=(
            f"{result.total_computed} balanços calculados, "
            f"{result.total_failed} falhas."
        ),
    )


# ─────────────────────────────────────────────────────────────────────────────
# Calcular todos os transformadores
# ─────────────────────────────────────────────────────────────────────────────

@router.post(
    "/all",
    response_model=APIResponse[BatchBalanceResponse],
    summary="Calcular Balanço para Todos os Transformadores",
    description=(
        "Calcula o balanço energético para todos os transformadores cadastrados. "
        "Recomendado para execução agendada diária."
    ),
    dependencies=[EngineeringRequired],
)
async def compute_all_balances(
    session: Annotated[AsyncSession, Depends(get_db_session)],
    period_start: datetime = Query(..., description="ISO 8601"),
    period_end: datetime = Query(..., description="ISO 8601"),
    force_recalculate: bool = Query(default=False),
) -> APIResponse[BatchBalanceResponse]:
    if period_start >= period_end:
        raise ValidationException(
            message="period_start deve ser anterior a period_end.",
            details={},
        )

    service = EnergyBalanceService(session)
    result = await service.compute_all_transformers(
        period_start=period_start,
        period_end=period_end,
        force_recalculate=force_recalculate,
    )

    return APIResponse(
        data=result,
        message=f"{result.total_computed}/{result.total_requested} transformadores calculados.",
    )


# ─────────────────────────────────────────────────────────────────────────────
# Sumário analítico
# ─────────────────────────────────────────────────────────────────────────────

@router.get(
    "/summary",
    response_model=APIResponse[BalanceSummaryResponse],
    summary="Sumário Analítico do Período",
    description=(
        "Retorna estatísticas agregadas dos balanços energéticos "
        "de todos os transformadores no período informado."
    ),
)
async def get_balance_summary(
    _: CurrentUser,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    period_start: datetime = Query(..., description="ISO 8601"),
    period_end: datetime = Query(..., description="ISO 8601"),
) -> APIResponse[BalanceSummaryResponse]:
    service = EnergyBalanceService(session)
    summary = await service.get_balance_summary(period_start, period_end)
    return APIResponse(
        data=summary,
        message=f"Sumário de {summary.transformer_count} transformadores.",
    )


# ─────────────────────────────────────────────────────────────────────────────
# Disparo assíncrono via Celery
# ─────────────────────────────────────────────────────────────────────────────

@router.post(
    "/async",
    summary="Disparar Cálculo Assíncrono",
    description=(
        "Envia o cálculo de balanço para a fila Celery. "
        "Retorna o task_id para monitoramento via endpoint de jobs."
    ),
    dependencies=[EngineeringRequired],
)
async def trigger_async_balance(
    body: BalanceComputeRequest,
) -> APIResponse[dict]:
    from backend.workers.tasks.balance_tasks import task_compute_transformer_balance

    task = task_compute_transformer_balance.delay(
        transformer_id=body.transformer_id,
        period_start_iso=body.period_start.isoformat(),
        period_end_iso=body.period_end.isoformat(),
        force_recalculate=body.force_recalculate,
    )

    logger.info(
        "api.balance.async_triggered",
        transformer_id=body.transformer_id,
        task_id=task.id,
    )
    return APIResponse(
        data={"task_id": task.id, "status": "queued"},
        message="Cálculo enviado para fila de processamento.",
    )
