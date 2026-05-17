import structlog
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from backend.api.deps import get_current_user, get_db
from backend.schemas.validation import (
    ValidationRequest,
    ValidationResponse,
    AnomalyDetectionRequest,
    AnomalyDetectionResponse,
    CalibrationRequest,
    CalibrationResponse,
    ValidationHistoryResponse,
    CalibrationHistoryResponse,
)
from backend.services.validation_service import ValidationService
from backend.repositories.validation_repository import (
    ValidationRepository,
    AnomalyRepository,
)
from backend.repositories.calibration_repository import CalibrationRepository
from backend.workers.validation_worker import (
    run_validation_task,
    run_calibration_task,
)

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/validation", tags=["Validação Real"])


@router.post(
    "/transformer",
    response_model=ValidationResponse,
    summary="Validar balanço estimado vs medido de um transformador",
    description=(
        "Compara o balanço energético estimado com a medição real do transformador. "
        "Calcula erro absoluto, erro percentual e desvio sazonal. "
        "Persiste o registro de validação e retorna o score operacional."
    ),
)
def validate_transformer(
    request: ValidationRequest,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
) -> ValidationResponse:
    logger.info(
        "api.validate_transformer",
        transformer_id=request.transformer_id,
        user=getattr(current_user, "matricula", "unknown"),
    )
    try:
        service = ValidationService(db)
        return service.validate_transformer(request)
    except Exception as exc:
        logger.error("api.validate_transformer.error", error=str(exc))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        )


@router.post(
    "/transformer/async",
    status_code=status.HTTP_202_ACCEPTED,
    summary="Validação assíncrona via Celery",
)
def validate_transformer_async(
    request: ValidationRequest,
    current_user=Depends(get_current_user),
) -> dict:
    task = run_validation_task.apply_async(
        kwargs={
            "transformer_id": request.transformer_id,
            "request_data": request.model_dump(mode="json"),
        }
    )
    logger.info(
        "api.validate_transformer_async.queued",
        task_id=task.id,
        transformer_id=request.transformer_id,
    )
    return {
        "task_id": task.id,
        "transformer_id": request.transformer_id,
        "status": "queued",
    }


@router.get(
    "/transformer/{transformer_id}/history",
    response_model=ValidationHistoryResponse,
    summary="Histórico de validações de um transformador",
)
def get_validation_history(
    transformer_id: str,
    limit: int = Query(default=30, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
) -> ValidationHistoryResponse:
    repo = ValidationRepository(db)
    records = repo.get_by_transformer(transformer_id, limit=limit)

    return ValidationHistoryResponse(
        transformer_id=transformer_id,
        total_records=len(records),
        records=[ValidationResponse.model_validate(r) for r in records],
    )


@router.post(
    "/anomaly",
    response_model=AnomalyDetectionResponse,
    summary="Detectar anomalia energética em uma UC",
    description=(
        "Executa Isolation Forest e One-Class SVM sobre o vetor de features da UC. "
        "Retorna resultado de consenso, scores individuais e recomendação operacional."
    ),
)
def detect_anomaly(
    request: AnomalyDetectionRequest,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
) -> AnomalyDetectionResponse:
    logger.info(
        "api.detect_anomaly",
        uc_code=request.uc_code,
        transformer_id=request.transformer_id,
    )
    try:
        service = ValidationService(db)
        return service.detect_anomaly(request, db)
    except Exception as exc:
        logger.error("api.detect_anomaly.error", error=str(exc))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        )


@router.get(
    "/anomaly/{transformer_id}/active",
    summary="Listar anomalias ativas de um transformador",
)
def list_active_anomalies(
    transformer_id: str,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
) -> dict:
    repo = AnomalyRepository(db)
    records = repo.get_active_by_transformer(transformer_id)
    count = repo.get_unresolved_count(transformer_id)

    return {
        "transformer_id": transformer_id,
        "total_active": count,
        "anomalies": [
            {
                "id": r.id,
                "uc_code": r.uc_code,
                "is_anomaly": r.is_anomaly,
                "consensus": r.consensus,
                "final_score": r.final_score,
                "recommendation": r.recommendation,
                "detected_at": r.detected_at.isoformat(),
            }
            for r in records
        ],
    }


@router.patch(
    "/anomaly/{record_id}/resolve",
    summary="Resolver anomalia após inspeção de campo",
)
def resolve_anomaly(
    record_id: int,
    resolved_by: str = Query(...),
    notes: str = Query(default=None),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
) -> dict:
    repo = AnomalyRepository(db)
    record = repo.resolve(record_id, resolved_by=resolved_by, notes=notes)
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Anomalia {record_id} não encontrada",
        )
    return {
        "id": record.id,
        "resolved": True,
        "resolved_by": record.resolved_by,
        "resolved_at": record.resolved_at.isoformat() if record.resolved_at else None,
    }


@router.post(
    "/calibrate",
    response_model=CalibrationResponse,
    summary="Calibrar fatores kWp e perdas técnicas com medições reais",
    description=(
        "Recebe feedback de UCs telemedidas e executa ciclo de calibração. "
        "Atualiza fator kWp por transformador e fator de perdas técnicas. "
        "Persiste histórico de calibração e retorna resultado do ciclo."
    ),
)
def calibrate(
    request: CalibrationRequest,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
) -> CalibrationResponse:
    logger.info(
        "api.calibrate",
        transformer_id=request.transformer_id,
        records=len(request.feedback_records),
    )
    try:
        service = ValidationService(db)
        return service.run_calibration(request, db)
    except Exception as exc:
        logger.error("api.calibrate.error", error=str(exc))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        )


@router.post(
    "/calibrate/async",
    status_code=status.HTTP_202_ACCEPTED,
    summary="Calibração assíncrona via Celery",
)
def calibrate_async(
    request: CalibrationRequest,
    current_user=Depends(get_current_user),
) -> dict:
    task = run_calibration_task.apply_async(
        kwargs={
            "transformer_id": request.transformer_id,
            "request_data": request.model_dump(mode="json"),
        }
    )
    return {
        "task_id": task.id,
        "transformer_id": request.transformer_id,
        "status": "queued",
    }


@router.get(
    "/calibrate/{transformer_id}/history",
    response_model=CalibrationHistoryResponse,
    summary="Histórico de calibrações de um transformador",
)
def get_calibration_history(
    transformer_id: str,
    limit: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
) -> CalibrationHistoryResponse:
    repo = CalibrationRepository(db)
    latest = repo.get_latest(transformer_id)
    history = repo.get_history(transformer_id, limit=limit)

    return CalibrationHistoryResponse(
        transformer_id=transformer_id,
        total_cycles=len(history),
        latest_kwp_factor=latest.kwp_factor_new if latest else None,
        latest_loss_factor=latest.loss_factor_new if latest else None,
        converged=latest.converged if latest else False,
        history=[
            {
                "id": h.id,
                "kwp_factor_old": h.kwp_factor_old,
                "kwp_factor_new": h.kwp_factor_new,
                "kwp_factor_delta": h.kwp_factor_delta,
                "loss_factor_new": h.loss_factor_new,
                "samples_used": h.samples_used,
                "mean_kwp_error_pct": h.mean_kwp_error_pct,
                "converged": h.converged,
                "executed_at": h.executed_at.isoformat(),
                "notes": h.notes,
            }
            for h in history
        ],
    )


@router.get(
    "/task/{task_id}",
    summary="Consultar status de tarefa de validação assíncrona",
)
def get_task_status(
    task_id: str,
    current_user=Depends(get_current_user),
) -> dict:
    from celery.result import AsyncResult
    from backend.core.celery_app import celery_app

    result = AsyncResult(task_id, app=celery_app)
    return {
        "task_id": task_id,
        "status": result.state.lower(),
        "result": result.result if result.state == "SUCCESS" else None,
        "error": str(result.result) if result.state == "FAILURE" else None,
    }
