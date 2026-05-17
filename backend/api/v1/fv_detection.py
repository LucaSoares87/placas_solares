import structlog
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from typing import Optional

import numpy as np

from backend.api.deps import get_current_user
from backend.schemas.fv_detection import (
    FVDetectionRequest,
    FVDetectionResponse,
    FVDetectionAsyncResponse,
    FVTaskStatusResponse,
    GeoReferenceInput,
)
from backend.services.fv_detection_service import FVDetectionService
from backend.workers.fv_worker import run_fv_detection_task
from backend.core.config import settings

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/fv", tags=["Visão Computacional — FV"])

MAX_IMAGE_BYTES = settings.YOLO_MAX_IMAGE_SIZE_MB * 1024 * 1024


def _read_image_bytes(upload: UploadFile) -> bytes:
    image_bytes = upload.file.read()
    if len(image_bytes) > MAX_IMAGE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"Imagem excede o limite de {settings.YOLO_MAX_IMAGE_SIZE_MB}MB",
        )
    return image_bytes


def _decode_image(image_bytes: bytes) -> np.ndarray:
    try:
        import cv2
        nparr = np.frombuffer(image_bytes, np.uint8)
        image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        if image is None:
            raise ValueError("Imagem inválida")
        return image
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Não foi possível decodificar a imagem: {exc}",
        )


@router.post(
    "/detect",
    response_model=FVDetectionResponse,
    summary="Detectar painéis FV em imagem aérea (síncrono)",
    description=(
        "Recebe uma imagem aérea e metadados da UC. "
        "Executa detecção YOLO, segmentação, conversão pixel→m² e estimativa kWp. "
        "Retorna resultado completo de forma síncrona. "
        "Para imagens grandes, prefira o endpoint assíncrono /fv/detect-async."
    ),
)
async def detect_fv_sync(
    uc_code: str = Form(...),
    transformer_id: str = Form(...),
    latitude: float = Form(...),
    longitude: float = Form(...),
    gsd_m_per_pixel: Optional[float] = Form(None),
    altitude_m: Optional[float] = Form(None),
    focal_length_mm: Optional[float] = Form(None),
    sensor_width_mm: Optional[float] = Form(None),
    image_width_px: Optional[int] = Form(None),
    perspective_correction: float = Form(1.0),
    distortion_correction: float = Form(1.0),
    regional_kwp_factor: Optional[float] = Form(None),
    confidence_threshold: float = Form(0.45),
    image: UploadFile = File(..., description="Imagem aérea da UC (JPG/PNG/TIFF)"),
    current_user=Depends(get_current_user),
) -> FVDetectionResponse:
    logger.info(
        "api.fv_detect_sync",
        uc_code=uc_code,
        user=getattr(current_user, "matricula", "unknown"),
    )

    image_bytes = _read_image_bytes(image)
    decoded_image = _decode_image(image_bytes)

    geo_reference = GeoReferenceInput(
        gsd_m_per_pixel=gsd_m_per_pixel,
        altitude_m=altitude_m,
        focal_length_mm=focal_length_mm,
        sensor_width_mm=sensor_width_mm,
        image_width_px=image_width_px,
        perspective_correction=perspective_correction,
        distortion_correction=distortion_correction,
    )

    request = FVDetectionRequest(
        uc_code=uc_code,
        transformer_id=transformer_id,
        latitude=latitude,
        longitude=longitude,
        geo_reference=geo_reference,
        regional_kwp_factor=regional_kwp_factor,
        confidence_threshold=confidence_threshold,
    )

    try:
        service = FVDetectionService()
        result = service.run(request=request, image=decoded_image)
        return result
    except RuntimeError as exc:
        logger.error("api.fv_detect_sync.error", error=str(exc))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        )


@router.post(
    "/detect-async",
    response_model=FVDetectionAsyncResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Detectar painéis FV de forma assíncrona (Celery)",
    description=(
        "Envia a detecção FV para processamento assíncrono via Celery. "
        "Retorna um task_id para consulta posterior em /fv/task/{task_id}."
    ),
)
async def detect_fv_async(
    uc_code: str = Form(...),
    transformer_id: str = Form(...),
    latitude: float = Form(...),
    longitude: float = Form(...),
    gsd_m_per_pixel: Optional[float] = Form(None),
    altitude_m: Optional[float] = Form(None),
    focal_length_mm: Optional[float] = Form(None),
    sensor_width_mm: Optional[float] = Form(None),
    image_width_px: Optional[int] = Form(None),
    perspective_correction: float = Form(1.0),
    distortion_correction: float = Form(1.0),
    regional_kwp_factor: Optional[float] = Form(None),
    confidence_threshold: float = Form(0.45),
    transformer_kwp_factor: Optional[float] = Form(None),
    cluster_kwp_factor: Optional[float] = Form(None),
    image: UploadFile = File(...),
    current_user=Depends(get_current_user),
) -> FVDetectionAsyncResponse:
    logger.info(
        "api.fv_detect_async",
        uc_code=uc_code,
        user=getattr(current_user, "matricula", "unknown"),
    )

    image_bytes = _read_image_bytes(image)

    request_data = {
        "uc_code": uc_code,
        "transformer_id": transformer_id,
        "latitude": latitude,
        "longitude": longitude,
        "geo_reference": {
            "gsd_m_per_pixel": gsd_m_per_pixel,
            "altitude_m": altitude_m,
            "focal_length_mm": focal_length_mm,
            "sensor_width_mm": sensor_width_mm,
            "image_width_px": image_width_px,
            "perspective_correction": perspective_correction,
            "distortion_correction": distortion_correction,
        },
        "regional_kwp_factor": regional_kwp_factor,
        "confidence_threshold": confidence_threshold,
    }

    task = run_fv_detection_task.apply_async(
        kwargs={
            "request_data": request_data,
            "image_bytes": image_bytes,
            "transformer_kwp_factor": transformer_kwp_factor,
            "cluster_kwp_factor": cluster_kwp_factor,
        }
    )

    logger.info("api.fv_detect_async.queued", task_id=task.id, uc_code=uc_code)

    return FVDetectionAsyncResponse(
        task_id=task.id,
        uc_code=uc_code,
        status="queued",
        message="Detecção FV enviada para processamento assíncrono",
    )


@router.get(
    "/task/{task_id}",
    response_model=FVTaskStatusResponse,
    summary="Consultar status de tarefa FV assíncrona",
)
async def get_fv_task_status(
    task_id: str,
    current_user=Depends(get_current_user),
) -> FVTaskStatusResponse:
    from celery.result import AsyncResult
    from backend.core.celery_app import celery_app

    result = AsyncResult(task_id, app=celery_app)

    if result.state == "PENDING":
        return FVTaskStatusResponse(task_id=task_id, status="pending")

    if result.state == "STARTED":
        return FVTaskStatusResponse(task_id=task_id, status="running")

    if result.state == "SUCCESS":
        from backend.schemas.fv_detection import FVDetectionResponse
        return FVTaskStatusResponse(
            task_id=task_id,
            status="success",
            result=FVDetectionResponse(**result.result),
        )

    if result.state == "FAILURE":
        return FVTaskStatusResponse(
            task_id=task_id,
            status="failed",
            error=str(result.result),
        )

    return FVTaskStatusResponse(task_id=task_id, status=result.state.lower())


@router.get(
    "/health",
    summary="Health check do módulo FV",
    include_in_schema=False,
)
async def fv_health():
    from pathlib import Path
    model_exists = Path(settings.YOLO_MODEL_PATH).exists()
    return {
        "module": "fv_detection",
        "model_path": settings.YOLO_MODEL_PATH,
        "model_loaded": model_exists,
        "confidence_threshold": settings.YOLO_CONFIDENCE_THRESHOLD,
    }
