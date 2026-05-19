"""
Task: reprocessamento de um transformador — invalida inferências antigas
e dispara novo batch.
"""

from __future__ import annotations


import structlog

from backend.repositories.batch_job_repository import BatchJobRepository
from backend.worker.context import db_session
from backend.core.queue import enqueue

logger = structlog.get_logger(__name__)


async def reprocess_transformer(
    ctx: dict,
    *,
    job_id: str,
    transformer_id: str,
    measured_kwh: float,
    period_start: str,
    period_end: str,
    requested_by: str = "system",
) -> dict:
    """
    ARQ task — reprocessa o balanço de um transformador.

    Invalida o job de batch anterior (se existir) e enfileira novo batch.
    """
    log = logger.bind(job_id=job_id, transformer_id=transformer_id)
    log.info("reprocess.started", requested_by=requested_by)

    async with db_session(ctx) as session:
        job_repo = BatchJobRepository(session)

        await job_repo.create_job(
            job_id=job_id,
            job_type="reprocess",
            transformer_id=transformer_id,
            total_items=1,
        )
        await job_repo.mark_running(job_id)

    # Deduplicação: job_id determinístico para evitar duplicatas
    new_batch_job_id = f"batch:{transformer_id}:{period_start}"

    enqueued = await enqueue(
        "run_batch_inference_for_transformer",
        job_id=new_batch_job_id,
        transformer_id=transformer_id,
        measured_kwh=measured_kwh,
        period_start=period_start,
        period_end=period_end,
        _job_id=new_batch_job_id,
    )

    async with db_session(ctx) as session:
        job_repo = BatchJobRepository(session)
        summary = f"enqueued_batch_job_id={new_batch_job_id}"
        await job_repo.mark_success(
            job_id, processed=1, failed=0, summary=summary
        )

    log.info("reprocess.finished", new_batch_job_id=new_batch_job_id)
    return {
        "job_id": job_id,
        "transformer_id": transformer_id,
        "new_batch_job_id": new_batch_job_id,
        "enqueued": enqueued is not None,
    }
