"""
Tasks Celery para coleta assíncrona de dados climáticos.
"""

from __future__ import annotations

import structlog
from celery import shared_task

logger = structlog.get_logger(__name__)


@shared_task(
    name="climate.fetch_transformer",
    bind=True,
    max_retries=3,
    default_retry_delay=120,
    acks_late=True,
)
def task_fetch_transformer_climate(
    self,
    transformer_id: str,
    date_start_iso: str,
    date_end_iso: str,
    force_refresh: bool = False,
) -> dict:
    import asyncio
    from datetime import date
    from backend.services.climate_service import ClimateService
    from backend.core.database import get_async_session_context
    from backend.core.redis import get_redis_client

    date_start = date.fromisoformat(date_start_iso)
    date_end = date.fromisoformat(date_end_iso)

    async def _run():
        async with get_async_session_context() as session:
            redis = await get_redis_client()
            service = ClimateService(session, redis)
            result = await service.fetch_for_transformer(
                transformer_id=transformer_id,
                date_start=date_start,
                date_end=date_end,
                force_refresh=force_refresh,
            )
            return {
                "transformer_id": transformer_id,
                "total_days": result.total_days,
                "avg_irradiance_kwh_m2": result.avg_irradiance_kwh_m2,
                "source": result.source,
            }

    try:
        result = asyncio.get_event_loop().run_until_complete(_run())
        logger.info("climate.task.completed", **result)
        return result
    except Exception as exc:
        logger.error(
            "climate.task.failed",
            transformer_id=transformer_id,
            error=str(exc),
        )
        raise self.retry(exc=exc)


@shared_task(
    name="climate.fetch_all_transformers",
    bind=True,
    max_retries=2,
    default_retry_delay=300,
    acks_late=True,
)
def task_fetch_all_climate(
    self,
    date_start_iso: str,
    date_end_iso: str,
    force_refresh: bool = False,
) -> dict:
    """
    Coleta dados climáticos para todos os transformadores cadastrados.
    Agendado diariamente para manter o banco atualizado.
    """
    import asyncio
    from datetime import date
    from backend.services.climate_service import ClimateService
    from backend.repositories.energy_balance_repository import EnergyBalanceRepository
    from backend.core.database import get_async_session_context
    from backend.core.redis import get_redis_client

    date_start = date.fromisoformat(date_start_iso)
    date_end = date.fromisoformat(date_end_iso)

    async def _run():
        async with get_async_session_context() as session:
            redis = await get_redis_client()
            balance_repo = EnergyBalanceRepository(session)
            transformer_ids = await balance_repo.get_transformer_ids_all()

            climate_service = ClimateService(session, redis)
            results = {"success": 0, "failed": 0, "transformers": len(transformer_ids)}

            for tid in transformer_ids:
                try:
                    await climate_service.fetch_for_transformer(
                        transformer_id=tid,
                        date_start=date_start,
                        date_end=date_end,
                        force_refresh=force_refresh,
                    )
                    results["success"] += 1
                except Exception as exc:
                    results["failed"] += 1
                    logger.warning(
                        "climate.task.transformer_failed",
                        transformer_id=tid,
                        error=str(exc),
                    )

            return results

    try:
        result = asyncio.get_event_loop().run_until_complete(_run())
        logger.info("climate.task.all_completed", **result)
        return result
    except Exception as exc:
        logger.error("climate.task.all_failed", error=str(exc))
        raise self.retry(exc=exc)
