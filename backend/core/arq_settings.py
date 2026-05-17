"""Configuração central do ARQ (Redis-based task queue)."""

from arq.connections import RedisSettings

from backend.core.config import settings


def get_redis_settings() -> RedisSettings:
    return RedisSettings(
        host=settings.REDIS_HOST,
        port=settings.REDIS_PORT,
        password=settings.REDIS_PASSWORD or None,
        database=settings.REDIS_DB,
    )


class WorkerSettings:
    """
    Classe de configuração do worker ARQ.
    Importada pelo comando `arq backend.core.arq_settings.WorkerSettings`.
    """

    redis_settings = get_redis_settings()

    # Funções registradas no worker
    functions = []          # preenchido em arq_worker.py via importação dinâmica

    # Limites operacionais
    max_jobs = 10           # máximo de jobs paralelos
    job_timeout = 300       # timeout por job em segundos
    keep_result = 3600      # tempo de retenção do resultado no Redis (1h)
    max_tries = 3           # tentativas em caso de falha

    # Saúde do worker
    health_check_interval = 30
    health_check_key = "arq:health:unidades_geradoras"

    on_startup = None       # referenciado em arq_worker.py
    on_shutdown = None
