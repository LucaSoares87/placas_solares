from celery import Celery

from backend.core.config import get_settings

settings = get_settings()

celery_app = Celery(
    "energy_platform",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=["backend.workers.tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="America/Sao_Paulo",
    enable_utc=True,
    task_soft_time_limit=settings.celery_task_soft_time_limit,
    task_time_limit=settings.celery_task_time_limit,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    task_routes={
        "backend.workers.tasks.run_fv_inference": {"queue": "ml"},
        "backend.workers.tasks.run_balance_calculation": {"queue": "energy"},
        "backend.workers.tasks.run_weather_sync": {"queue": "data"},
    },
)
