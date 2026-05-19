"""Configuração central do ARQ (Redis-based task queue)."""

from arq.connections import RedisSettings

from backend.core.config import settings


def get_redis_settings() -> RedisSettings:
    return RedisSettings(
        host=settings.redis_host,
        port=settings.redis_port,
        password=settings.redis_password or None,
        database=settings.redis_db,
    )


class WorkerSettings:
    """
    Classe de configuração do worker ARQ.
    Importada pelo comando `arq backend.core.arq_settings.WorkerSettings`.
    """

    redis_settings = get_redis_settings()

    # Funções registradas no worker
    functions = []

    # Limites operacionais
    max_jobs = settings.worker_max_jobs
    job_timeout = settings.worker_job_timeout
    keep_result = 3600
    max_tries = 3

    # Saúde do worker
    health_check_interval = 30
    health_check_key = "arq:health:unidades_geradoras"

    on_startup = None
    on_shutdown = None