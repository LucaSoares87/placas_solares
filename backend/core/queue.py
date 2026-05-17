"""
Interface centralizada para enfileirar jobs no ARQ.
Utilizado por endpoints e serviços para despachar tarefas assíncronas.
"""

from typing import Any

import structlog
from arq import ArqRedis, create_pool

from backend.core.arq_settings import get_redis_settings

logger = structlog.get_logger(__name__)

_pool: ArqRedis | None = None


async def get_queue() -> ArqRedis:
    global _pool
    if _pool is None:
        _pool = await create_pool(get_redis_settings())
        logger.info("arq.pool.created")
    return _pool


async def close_queue() -> None:
    global _pool
    if _pool:
        await _pool.aclose()
        _pool = None
        logger.info("arq.pool.closed")


async def enqueue(
    function_name: str,
    *args: Any,
    _job_id: str | None = None,
    _defer_by: float | None = None,
    **kwargs: Any,
) -> str | None:
    """
    Enfileira um job no ARQ com suporte a deduplicação por job_id.

    Returns:
        job_id gerado ou None se o job já existia (deduplicado).
    """
    pool = await get_queue()
    job = await pool.enqueue_job(
        function_name,
        *args,
        _job_id=_job_id,
        _defer_by=_defer_by,
        **kwargs,
    )
    if job:
        logger.info("arq.job.enqueued", function=function_name, job_id=job.job_id)
        return job.job_id

    logger.warning("arq.job.deduplicated", function=function_name, job_id=_job_id)
    return None


async def get_job_status(job_id: str) -> dict:
    pool = await get_queue()
    job = await pool.job(job_id)
    if not job:
        return {"job_id": job_id, "status": "not_found"}

    info = await job.info()
    result = None
    try:
        result = await job.result(timeout=0)
    except Exception:
        pass

    return {
        "job_id": job_id,
        "status": info.status.value if info else "unknown",
        "result": result,
        "enqueue_time": info.enqueue_time.isoformat() if info and info.enqueue_time else None,
        "start_time": info.start_time.isoformat() if info and info.start_time else None,
        "finish_time": info.finish_time.isoformat() if info and info.finish_time else None,
    }
