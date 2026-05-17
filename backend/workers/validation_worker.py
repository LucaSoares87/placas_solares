import structlog
from datetime import datetime

from backend.core.celery_app import celery_app

logger = structlog.get_logger(__name__)


@celery_app.task(
    name="workers.validation.run_validation",
    bind=True,
    max_retries=3,
    default_retry_delay=15,
    acks_late=True,
    track_started=True,
)
def run_validation_task(self, transformer_id: str, request_data: dict) -> dict:
    from backend.core.database import SessionLocal
    from backend.services.validation_service import ValidationService
    from backend.schemas.validation import ValidationRequest

    task_id = self.request.id
    logger.info(
        "validation_worker.started",
        task_id=task_id,
        transformer_id=transformer_id,
    )

    try:
        db = SessionLocal()
        try:
            request = ValidationRequest(**request_data)
            service = ValidationService(db)
            result = service.validate_transformer(request)

            logger.info(
                "validation_worker.completed",
                task_id=task_id,
                transformer_id=transformer_id,
                erro_pct=result.erro_percentual_pct,
                status=result.status_validacao,
            )
            return result.model_dump(mode="json")
        finally:
            db.close()

    except Exception as exc:
        logger.error(
            "validation_worker.failed",
            task_id=task_id,
            transformer_id=transformer_id,
            error=str(exc),
        )
        raise self.retry(exc=exc)


@celery_app.task(
    name="workers.validation.run_calibration",
    bind=True,
    max_retries=3,
    default_retry_delay=15,
    acks_late=True,
    track_started=True,
)
def run_calibration_task(self, transformer_id: str, request_data: dict) -> dict:
    from backend.core.database import SessionLocal
    from backend.services.validation_service import ValidationService
    from backend.schemas.validation import CalibrationRequest

    task_id = self.request.id
    logger.info(
        "calibration_worker.started",
        task_id=task_id,
        transformer_id=transformer_id,
    )

    try:
        db = SessionLocal()
        try:
            request = CalibrationRequest(**request_data)
            service = ValidationService(db)
            result = service.run_calibration(request, db)

            logger.info(
                "calibration_worker.completed",
                task_id=task_id,
                transformer_id=transformer_id,
                kwp_new=result.kwp_factor_new,
                converged=result.converged,
            )
            return result.model_dump(mode="json")
        finally:
            db.close()

    except Exception as exc:
        logger.error(
            "calibration_worker.failed",
            task_id=task_id,
            transformer_id=transformer_id,
            error=str(exc),
        )
        raise self.retry(exc=exc)
