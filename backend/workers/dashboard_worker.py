import structlog
from backend.core.celery_app import celery_app

logger = structlog.get_logger(__name__)


@celery_app.task(
    name="workers.dashboard.generate_snapshot",
    bind=True,
    max_retries=3,
    default_retry_delay=10,
    acks_late=True,
    track_started=True,
)
def generate_snapshot_task(self, transformer_id: str, request_data: dict) -> dict:
    from backend.core.database import SessionLocal
    from backend.services.dashboard_service import DashboardService
    from backend.services.alert_service import AlertService
    from backend.schemas.dashboard import SnapshotRequest

    task_id = self.request.id
    logger.info(
        "dashboard_worker.snapshot_start",
        task_id=task_id,
        transformer_id=transformer_id,
    )

    try:
        db = SessionLocal()
        try:
            request = SnapshotRequest(**request_data)
            service = DashboardService(db)
            result = service.generate_snapshot(request)

            alert_service = AlertService(db)
            alert_service.evaluate_snapshot(result.model_dump())

            logger.info(
                "dashboard_worker.snapshot_done",
                task_id=task_id,
                transformer_id=transformer_id,
                score=result.score_operacional,
            )
            return result.model_dump(mode="json")
        finally:
            db.close()

    except Exception as exc:
        logger.error(
            "dashboard_worker.snapshot_failed",
            task_id=task_id,
            transformer_id=transformer_id,
            error=str(exc),
        )
        raise self.retry(exc=exc)


@celery_app.task(
    name="workers.dashboard.refresh_all_snapshots",
    bind=True,
    max_retries=2,
    default_retry_delay=30,
    acks_late=True,
)
def refresh_all_snapshots_task(self, reference_period: str) -> dict:
    """
    Task periódica (Celery Beat) que dispara geração de snapshot
    para todos os transformadores ativos no período informado.
    """
    from backend.core.database import SessionLocal
    from backend.repositories.dashboard_repository import DashboardRepository

    task_id = self.request.id
    logger.info(
        "dashboard_worker.refresh_all_start",
        task_id=task_id,
        period=reference_period,
    )

    try:
        db = SessionLocal()
        try:
            repo = DashboardRepository(db)
            snapshots = repo.list_all_latest()
            transformer_ids = [s.transformer_id for s in snapshots]

            dispatched = 0
            for tid in transformer_ids:
                generate_snapshot_task.apply_async(
                    kwargs={
                        "transformer_id": tid,
                        "request_data": {
                            "transformer_id": tid,
                            "reference_period": reference_period,
                            "total_ucs": 0,
                            "total_ucs_fv": 0,
                        },
                    }
                )
                dispatched += 1

            logger.info(
                "dashboard_worker.refresh_all_done",
                dispatched=dispatched,
            )
            return {"dispatched": dispatched, "period": reference_period}
        finally:
            db.close()

    except Exception as exc:
        logger.error(
            "dashboard_worker.refresh_all_failed",
            error=str(exc),
        )
        raise self.retry(exc=exc)


@celery_app.task(
    name="workers.dashboard.export_csv",
    bind=True,
    max_retries=2,
    acks_late=True,
)
def export_csv_task(self, request_data: dict) -> str:
    from backend.core.database import SessionLocal
    from backend.services.export_service import ExportService
    from backend.schemas.dashboard import ExportRequest

    task_id = self.request.id
    logger.info("dashboard_worker.export_csv_start", task_id=task_id)

    try:
        db = SessionLocal()
        try:
            request = ExportRequest(**request_data)
            service = ExportService(db)
            csv_content = service.export_csv(request)
            logger.info(
                "dashboard_worker.export_csv_done",
                task_id=task_id,
                chars=len(csv_content),
            )
            return csv_content
        finally:
            db.close()

    except Exception as exc:
        logger.error(
            "dashboard_worker.export_csv_failed",
            task_id=task_id,
            error=str(exc),
        )
        raise self.retry(exc=exc)
