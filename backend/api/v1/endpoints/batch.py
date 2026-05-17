"""
Endpoints de controle do pipeline de processamento em lote.
Permite disparar jobs, consultar status e solicitar reprocessamentos.
"""

from typing import Annotated
from uuid import uuid4

import structlog
from fastapi import APIRouter, Depends, Path, Query
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.v1.dependencies import CurrentUser, EngineeringRequired
from backend.core.database import get_db_session
from backend.core.queue import enqueue, get_job_status
from backend.repositories.batch_job_repository import BatchJobRepository
from backend.schemas.batch_job import (
    BatchJobResponse,
    BatchJobStatusResponse,
    EnqueueBatchRequest,
    EnqueueReprocessRequest,
    EnqueueTelemetryRequest,
)
from backend.schemas.common import APIResponse, PaginatedResponse

router = APIRouter(prefix="/batch", tags=["Processamento em Lote"])
logger = structlog.get_logger(__name__)


@router.post(
    "/inference",
    response_model=APIResponse[dict],
    dependencies=[EngineeringRequired],
)
async def enqueue_batch_inference(
    body: EnqueueBatchRequest,
):
    """
    Enfileira um job de inferência em lote para todas as UCs de um transformador.
    Deduplicado por (transformer_id + period_start).
    """
    job_id = f"batch:{body.transformer_id}:{body.period_start.isoformat()}"

    enqueued = await enqueue(
        "run_batch_inference_for_transformer",
        job_id=job_id,
        transformer_id=body.transformer_id,
        measured_kwh=body.measured_kwh,
        period_start=body.period_start.isoformat(),
        period_end=body.period_end.isoformat(),
        _job_id=job_id,
    )

    return APIResponse(
        data={"job_id": job_id, "enqueued": enqueued is not None},
        message=(
            "Job enfileirado com sucesso."
            if enqueued
            else "Job já existe na fila (deduplicado)."
        ),
    )


@router.post(
    "/telemetry",
    response_model=APIResponse[dict],
    dependencies=[EngineeringRequired],
)
async def enqueue_telemetry_ingest(body: EnqueueTelemetryRequest):
    """
    Enfileira ingestão de leituras telemetradas em massa.
    """
    job_id = f"telemetry:{uuid4().hex}"

    enqueued = await enqueue(
        "ingest_telemetry_data",
        job_id=job_id,
        payloads=body.payloads,
        source_type=body.source_type,
        _job_id=job_id,
    )

    return APIResponse(
        data={"job_id": job_id, "total_payloads": len(body.payloads)},
        message="Ingestão de telemetria enfileirada.",
    )


@router.post(
    "/reprocess",
    response_model=APIResponse[dict],
    dependencies=[EngineeringRequired],
)
async def enqueue_reprocess(body: EnqueueReprocessRequest):
    """
    Solicita reprocessamento do balanço de um transformador.
    """
    job_id = f"reprocess:{body.transformer_id}:{uuid4().hex[:8]}"

    enqueued = await enqueue(
        "reprocess_transformer",
        job_id=job_id,
        transformer_id=body.transformer_id,
        measured_kwh=body.measured_kwh,
        period_start=body.period_start.isoformat(),
        period_end=body.period_end.isoformat(),
        _job_id=job_id,
    )

    return APIResponse(
        data={"job_id": job_id, "enqueued": enqueued is not None},
        message="Reprocessamento enfileirado.",
    )


@router.get(
    "/jobs/{job_id}/status",
    response_model=APIResponse[BatchJobStatusResponse],
)
async def get_job_status_endpoint(
    job_id: str = Path(...),
    _: CurrentUser = None,
):
    """Consulta o status de um job diretamente no Redis (ARQ)."""
    status = await get_job_status(job_id)
    return APIResponse(data=BatchJobStatusResponse(**status))


@router.get(
    "/jobs",
    response_model=PaginatedResponse[BatchJobResponse],
)
async def list_batch_jobs(
    _: CurrentUser,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    status: str | None = Query(None, description="Filtrar por status: pending | running | success | failed"),
    transformer_id: str | None = Query(None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
):
    """Lista jobs persistidos no banco com suporte a filtros."""
    repo = BatchJobRepository(session)
    offset = (page - 1) * page_size

    if transformer_id:
        items = await repo.list_by_transformer(transformer_id, offset, page_size)
    elif status:
        items = await repo.list_by_status(status, offset, page_size)
    else:
        items = await repo.list_all(offset, page_size)

    total = await repo.count_all()
    import math

    return PaginatedResponse(
        data=[BatchJobResponse.model_validate(i) for i in items],
        total=total,
        page=page,
        page_size=page_size,
        pages=math.ceil(total / page_size),
    )


@router.get(
    "/jobs/transformer/{transformer_id}",
    response_model=PaginatedResponse[BatchJobResponse],
)
async def list_jobs_by_transformer(
    transformer_id: str,
    _: CurrentUser,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
):
    """Lista jobs de um transformador específico."""
    import math
    repo = BatchJobRepository(session)
    offset = (page - 1) * page_size
    items = await repo.list_by_transformer(transformer_id, offset, page_size)
    total = len(items)

    return PaginatedResponse(
        data=[BatchJobResponse.model_validate(i) for i in items],
        total=total,
        page=page,
        page_size=page_size,
        pages=math.ceil(total / page_size) if total else 1,
    )
