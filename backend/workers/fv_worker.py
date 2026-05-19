import structlog
from typing import Optional

import numpy as np

from backend.core.celery_app import celery_app
from backend.schemas.fv_detection import FVDetectionRequest

logger = structlog.get_logger(__name__)


def _load_image_from_bytes(image_bytes: bytes) -> np.ndarray:
    try:
        import cv2
        nparr = np.frombuffer(image_bytes, np.uint8)
        image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        if image is None:
            raise ValueError("Imagem inválida ou corrompida")
        return image
    except ImportError as exc:
        raise ImportError("opencv-python é necessário no worker") from exc


@celery_app.task(
    name="workers.fv_detection.run_detection",
    bind=True,
    max_retries=3,
    default_retry_delay=10,
    acks_late=True,
    track_started=True,
)
def run_fv_detection_task(
    self,
    request_data: dict,
    image_bytes: bytes,
    transformer_kwp_factor: Optional[float] = None,
    cluster_kwp_factor: Optional[float] = None,
) -> dict:
    from backend.services.fv_detection_service import FVDetectionService

    task_id = self.request.id

    logger.info(
        "fv_worker.started",
        task_id=task_id,
        uc_code=request_data.get("uc_code"),
    )

    try:
        request = FVDetectionRequest(**request_data)
        image = _load_image_from_bytes(image_bytes)
        service = FVDetectionService()

        result = service.run(
            request=request,
            image=image,
            transformer_kwp_factor=transformer_kwp_factor,
            cluster_kwp_factor=cluster_kwp_factor,
        )

        result_dict = result.model_dump()
        result_dict["task_id"] = task_id

        logger.info(
            "fv_worker.completed",
            task_id=task_id,
            uc_code=request_data.get("uc_code"),
            has_fv=result.has_fv,
            kwp_adjusted=result.kwp_adjusted,
        )

        return result_dict

    except Exception as exc:
        logger.error(
            "fv_worker.failed",
            task_id=task_id,
            uc_code=request_data.get("uc_code"),
            error=str(exc),
        )
        raise self.retry(exc=exc)
