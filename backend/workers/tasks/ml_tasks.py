"""
Tasks Celery para treinamento e predição assíncrona de modelos ML.
"""

from __future__ import annotations

import structlog
from celery import shared_task

logger = structlog.get_logger(__name__)


@shared_task(
    name="ml.train",
    bind=True,
    max_retries=1,
    acks_late=True,
    time_limit=3600,        # 1 hora máximo para treinamento
    soft_time_limit=3300,
)
def task_train_model(
    self,
    model_type: str,
    target: str,
    transformer_ids: list[str] | None = None,
    date_start_iso: str | None = None,
    date_end_iso: str | None = None,
    n_estimators: int = 200,
    max_depth: int = 6,
    learning_rate: float = 0.05,
) -> dict:
    import asyncio
    from datetime import date
    from backend.domain.ml_model import ModelType, PredictionTarget, TrainingConfig
    from backend.services.ml_service import MlService
    from backend.core.database import get_async_session_context

    config = TrainingConfig(
        model_type=ModelType(model_type),
        target=PredictionTarget(target),
        n_estimators=n_estimators,
        max_depth=max_depth,
        learning_rate=learning_rate,
    )

    date_start = date.fromisoformat(date_start_iso) if date_start_iso else None
    date_end = date.fromisoformat(date_end_iso) if date_end_iso else None

    async def _run():
        async with get_async_session_context() as session:
            service = MlService(session)
            result = await service.train(
                config=config,
                transformer_ids=transformer_ids,
                date_start=date_start,
                date_end=date_end,
            )
            return {
                "version": result.version,
                "status": result.status,
                "acceptable": result.acceptable,
                "r2": result.metrics.get("r2"),
                "mae": result.metrics.get("mae"),
                "n_samples": result.n_samples,
            }

    try:
        result = asyncio.get_event_loop().run_until_complete(_run())
        logger.info("ml.task.train.completed", **result)
        return result
    except Exception as exc:
        logger.error("ml.task.train.failed", error=str(exc))
        raise self.retry(exc=exc)


@shared_task(
    name="ml.predict_batch",
    bind=True,
    max_retries=2,
    default_retry_delay=60,
    acks_late=True,
)
def task_predict_batch(
    self,
    transformer_ids: list[str],
    ref_date_iso: str,
    target: str,
) -> dict:
    import asyncio
    from datetime import date
    from backend.domain.ml_model import PredictionTarget
    from backend.services.ml_service import MlService
    from backend.core.database import get_async_session_context

    async def _run():
        async with get_async_session_context() as session:
            service = MlService(session)
            result = await service.predict_batch(
                transformer_ids=transformer_ids,
                ref_date=date.fromisoformat(ref_date_iso),
                target=PredictionTarget(target),
            )
            return {
                "total": result.total,
                "success": result.success,
                "failed": result.failed,
                "anomalies_detected": result.anomalies_detected,
            }

    try:
        result = asyncio.get_event_loop().run_until_complete(_run())
        logger.info("ml.task.predict_batch.completed", **result)
        return result
    except Exception as exc:
        logger.error("ml.task.predict_batch.failed", error=str(exc))
        raise self.retry(exc=exc)


@shared_task(
    name="ml.daily_retrain",
    bind=True,
    max_retries=1,
    acks_late=True,
    time_limit=7200,
)
def task_daily_retrain(self) -> dict:
    """
    Retreinamento diário agendado para todos os targets.
    Invocado pelo Celery Beat à meia-noite.
    """
    import asyncio
    from backend.domain.ml_model import ModelType, PredictionTarget, TrainingConfig
    from backend.services.ml_service import MlService
    from backend.core.database import get_async_session_context

    targets = [
        PredictionTarget.ENERGY_LOSS_PCT,
        PredictionTarget.ADJUSTED_BALANCE,
    ]

    async def _run():
        results = {}
        async with get_async_session_context() as session:
            service = MlService(session)
            for tgt in targets:
                config = TrainingConfig(
                    model_type=ModelType.GRADIENT_BOOSTING,
                    target=tgt,
                )
                try:
                    res = await service.train(config=config)
                    results[tgt.value] = {
                        "version": res.version,
                        "acceptable": res.acceptable,
                        "r2": res.metrics.get("r2"),
                    }
                except Exception as exc:
                    results[tgt.value] = {"error": str(exc)}
                    logger.error(
                        "ml.daily_retrain.target_failed",
                        target=tgt.value,
                        error=str(exc),
                    )
        return results

    try:
        result = asyncio.get_event_loop().run_until_complete(_run())
        logger.info("ml.daily_retrain.completed", result=result)
        return result
    except Exception as exc:
        logger.error("ml.daily_retrain.failed", error=str(exc))
        raise self.retry(exc=exc)
