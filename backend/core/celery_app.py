from celery import Celery

from backend.core.config import settings


def create_celery_app() -> Celery:
    app = Celery(
        "energy_inference_platform",
        broker=settings.celery_broker_url,
        backend=settings.celery_result_backend,
        include=[
            "backend.workers.fv_worker",
            "backend.workers.dashboard_worker",
            "backend.workers.export_worker",
            "backend.workers.validation_worker",
            "backend.workers.alert_worker",
            "backend.workers.calibration_worker",
            "backend.workers.tasks.balance_tasks",
            "backend.workers.tasks.batch_inference",
            "backend.workers.tasks.climate_tasks",
            "backend.workers.tasks.ml_tasks",
            "backend.workers.tasks.reprocess",
            "backend.workers.tasks.telemetry_ingest",
        ],
    )

    app.conf.update(
        task_serializer="json",
        accept_content=["json"],
        result_serializer="json",
        timezone="America/Recife",
        enable_utc=True,
        task_track_started=True,
        task_soft_time_limit=settings.celery_task_soft_time_limit,
        task_time_limit=settings.celery_task_time_limit,
        worker_prefetch_multiplier=1,
        task_acks_late=True,
    )

    return app


celery_app = create_celery_app()