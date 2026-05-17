"""
Ponto de entrada do worker ARQ.
Execute com: arq backend.core.arq_worker.WorkerSettings
"""

import structlog
from arq.connections import RedisSettings
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.arq_settings import get_redis_settings
from backend.core.config import settings
from backend.core.database import async_session_factory
from backend.worker.tasks.batch_inference import run_batch_inference_for_transformer
from backend.worker.tasks.telemetry_ingest import ingest_telemetry_data
from backend.worker.tasks.reprocess import reprocess_transformer
from backend.worker.tasks.alert_dispatcher import dispatch_alerts

logger = structlog.get_logger(__name__)


async def startup(ctx: dict) -> None:
    logger.info("arq.worker.startup", env=settings.ENV)
    ctx["db_factory"] = async_session_factory


async def shutdown(ctx: dict) -> None:
    logger.info("arq.worker.shutdown")


class WorkerSettings:
    redis_settings: RedisSettings = get_redis_settings()

    functions = [
        run_batch_inference_for_transformer,
        ingest_telemetry_data,
        reprocess_transformer,
        dispatch_alerts,
    ]

    max_jobs = 10
    job_timeout = 300
    keep_result = 3600
    max_tries = 3
    health_check_interval = 30
    health_check_key = "arq:health:unidades_geradoras"

    on_startup = startup
    on_shutdown = shutdown
