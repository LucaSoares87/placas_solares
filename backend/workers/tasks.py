import structlog
from celery import Task

from backend.workers.celery_app import celery_app

logger = structlog.get_logger(__name__)


class BaseTask(Task):
    abstract = True

    def on_failure(self, exc, task_id, args, kwargs, einfo):
        logger.error(
            "celery.task.failure",
            task_id=task_id,
            task_name=self.name,
            error=str(exc),
        )

    def on_success(self, retval, task_id, args, kwargs):
        logger.info(
            "celery.task.success",
            task_id=task_id,
            task_name=self.name,
        )


@celery_app.task(base=BaseTask, name="backend.workers.tasks.run_fv_inference", bind=True)
def run_fv_inference(self, uc_code: str) -> dict:
    logger.info("task.run_fv_inference.start", uc_code=uc_code)
    return {"uc_code": uc_code, "status": "queued"}


@celery_app.task(base=BaseTask, name="backend.workers.tasks.run_balance_calculation", bind=True)
def run_balance_calculation(self, transformer_id: str) -> dict:
    logger.info("task.run_balance_calculation.start", transformer_id=transformer_id)
    return {"transformer_id": transformer_id, "status": "queued"}


@celery_app.task(base=BaseTask, name="backend.workers.tasks.run_weather_sync", bind=True)
def run_weather_sync(self, latitude: float, longitude: float) -> dict:
    logger.info("task.run_weather_sync.start", lat=latitude, lon=longitude)
    return {"lat": latitude, "lon": longitude, "status": "queued"}
