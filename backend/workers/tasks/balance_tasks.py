"""
Tasks Celery para cálculo assíncrono de balanço energético.
Integra com o EnergyBalanceService via sessão independente.
"""

from __future__ import annotations

from datetime import datetime

import structlog
from celery import shared_task


logger = structlog.get_logger(__name__)


@shared_task(
    name="balance.compute_transformer",
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    acks_late=True,
)
def task_compute_transformer_balance(
    self,
    transformer_id: str,
    period_start_iso: str,
    period_end_iso: str,
    force_recalculate: bool = False,
) -> dict:
    """
    Task assíncrona para cálculo de balanço de um transformador.
    Executada pelo worker Celery.
    """
    import asyncio
    from backend.services.energy_balance_service import EnergyBalanceService
    from backend.core.database import get_async_session_context

    period_start = datetime.fromisoformat(period_start_iso)
    period_end = datetime.fromisoformat(period_end_iso)

    log = logger.bind(
        transformer_id=transformer_id,
        task_id=self.request.id,
    )

    async def _run():
        async with get_async_session_context() as session:
            service = EnergyBalanceService(session)
            result = await service.compute_transformer_balance(
                transformer_id=transformer_id,
                period_start=period_start,
                period_end=period_end,
                force_recalculate=force_recalculate,
            )
            return result.model_dump(mode="json")

    try:
        result = asyncio.get_event_loop().run_until_complete(_run())
        log.info("balance.task.completed", status=result.get("balance_status"))
        return result
    except Exception as exc:
        log.error("balance.task.failed", error=str(exc))
        raise self.retry(exc=exc)


@shared_task(
    name="balance.compute_all",
    bind=True,
    max_retries=2,
    default_retry_delay=120,
    acks_late=True,
)
def task_compute_all_balances(
    self,
    period_start_iso: str,
    period_end_iso: str,
    force_recalculate: bool = False,
) -> dict:
    """
    Task assíncrona para cálculo em lote de todos os transformadores.
    Tipicamente agendada diariamente.
    """
    import asyncio
    from backend.services.energy_balance_service import EnergyBalanceService
    from backend.core.database import get_async_session_context

    period_start = datetime.fromisoformat(period_start_iso)
    period_end = datetime.fromisoformat(period_end_iso)

    async def _run():
        async with get_async_session_context() as session:
            service = EnergyBalanceService(session)
            result = await service.compute_all_transformers(
                period_start=period_start,
                period_end=period_end,
                force_recalculate=force_recalculate,
            )
            return {
                "total_requested": result.total_requested,
                "total_computed": result.total_computed,
                "total_failed": result.total_failed,
                "computed_at": result.computed_at.isoformat(),
            }

    try:
        result = asyncio.get_event_loop().run_until_complete(_run())
        logger.info(
            "balance.task.all_completed",
            total_computed=result["total_computed"],
            task_id=self.request.id,
        )
        return result
    except Exception as exc:
        logger.error("balance.task.all_failed", error=str(exc))
        raise self.retry(exc=exc)
