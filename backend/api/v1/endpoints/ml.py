"""
Endpoints do módulo ML.

Rotas:
  POST /ml/train               → treinar modelo
  POST /ml/predict             → predição pontual
  POST /ml/predict/batch       → predição em lote
  GET  /ml/models              → listar versões de modelo
  GET  /ml/anomalies           → listar anomalias detectadas
  POST /ml/train/async         → treinamento assíncrono via Celery
  POST /ml/predict/batch/async → predição em lote via Celery
"""

from __future__ import annotations

from typing import Annotated

import structlog
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.v1.dependencies import CurrentUser, EngineeringRequired
from backend.core.database import get_db_session
from backend.core.exceptions import EntityNotFoundException, ValidationException
from backend.domain.ml_model import PredictionTarget, TrainingConfig
from backend.schemas.common import APIResponse
from backend.schemas.ml import (
    AnomalyResponse,
    BatchPredictRequest,
    BatchPredictionResponse,
    ModelVersionResponse,
    PredictRequest,
    PredictionResponse,
    TrainRequest,
    TrainResponse,
)
from backend.services.ml_service import MlService

router = APIRouter(prefix="/ml", tags=["Machine Learning"])
logger = structlog.get_logger(__name__)


@router.post(
    "/train",
    response_model=APIResponse[TrainResponse],
    summary="Treinar Modelo ML",
    description=(
        "Treina um novo modelo para o target especificado. "
        "Usa todos os dados históricos de balanço + clima disponíveis. "
        "O modelo é registrado automaticamente se atingir os critérios de qualidade."
    ),
    dependencies=[EngineeringRequired],
)
async def train_model(
    body: TrainRequest,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> APIResponse[TrainResponse]:
    config = TrainingConfig(
        model_type=body.model_type,
        target=body.target,
        test_size=body.test_size,
        split_strategy=body.split_strategy,
        n_estimators=body.n_estimators,
        max_depth=body.max_depth,
        learning_rate=body.learning_rate,
    )

    service = MlService(session)
    try:
        result = await service.train(
            config=config,
            transformer_ids=body.transformer_ids,
            date_start=body.date_start,
            date_end=body.date_end,
        )
    except ValueError as exc:
        raise ValidationException(message=str(exc), details={})

    logger.info(
        "api.ml.train.completed",
        version=result.version,
        status=result.status,
        r2=result.metrics.get("r2"),
    )
    status_msg = "Modelo registrado com sucesso." if result.acceptable \
        else "Modelo rejeitado por não atingir qualidade mínima."

    return APIResponse(data=result, message=status_msg)


@router.post(
    "/predict",
    response_model=APIResponse[PredictionResponse],
    summary="Predição Pontual",
    description="Executa predição ML para um transformador em uma data específica.",
)
async def predict(
    body: PredictRequest,
    _: CurrentUser,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> APIResponse[PredictionResponse]:
    service = MlService(session)
    try:
        result = await service.predict(
            transformer_id=body.transformer_id,
            ref_date=body.ref_date,
            target=body.target,
            actual_value=body.actual_value,
        )
    except ValueError as exc:
        raise EntityNotFoundException(
            message=str(exc),
            details={"transformer_id": body.transformer_id},
        )

    msg = (
        f"⚠️ Anomalia detectada (score {result.anomaly_score:.2f})."
        if result.is_anomaly
        else f"Predição calculada: {result.predicted_value:.4f}"
    )
    return APIResponse(data=result, message=msg)


@router.post(
    "/predict/batch",
    response_model=APIResponse[BatchPredictionResponse],
    summary="Predição em Lote",
    description="Executa predições ML para múltiplos transformadores.",
    dependencies=[EngineeringRequired],
)
async def predict_batch(
    body: BatchPredictRequest,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> APIResponse[BatchPredictionResponse]:
    service = MlService(session)
    result = await service.predict_batch(
        transformer_ids=body.transformer_ids,
        ref_date=body.ref_date,
        target=body.target,
    )
    return APIResponse(
        data=result,
        message=(
            f"{result.success}/{result.total} predições. "
            f"{result.anomalies_detected} anomalias detectadas."
        ),
    )


@router.get(
    "/models",
    response_model=APIResponse[list[ModelVersionResponse]],
    summary="Listar Versões do Modelo",
    dependencies=[EngineeringRequired],
)
async def list_model_versions(
    _: CurrentUser,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    target: PredictionTarget = Query(default=PredictionTarget.ENERGY_LOSS_PCT),
) -> APIResponse[list[ModelVersionResponse]]:
    from backend.repositories.ml_model_repository import MlModelRepository
    repo = MlModelRepository(session)
    versions = await repo.list_versions(target.value)
    data = [ModelVersionResponse(**v) for v in versions]
    return APIResponse(data=data, message=f"{len(data)} versões encontradas.")


@router.get(
    "/anomalies",
    response_model=APIResponse[list[AnomalyResponse]],
    summary="Anomalias Detectadas",
    description="Lista transformadores com anomalias detectadas pelo modelo ML.",
)
async def get_anomalies(
    _: CurrentUser,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    min_score: float = Query(default=2.0, ge=0.5),
    limit: int = Query(default=50, ge=1, le=200),
) -> APIResponse[list[AnomalyResponse]]:
    service = MlService(session)
    anomalies = await service.get_anomalies(min_score=min_score, limit=limit)
    data = [AnomalyResponse(**a) for a in anomalies]
    return APIResponse(
        data=data,
        message=f"{len(data)} anomalias com score ≥ {min_score}.",
    )


@router.post(
    "/train/async",
    summary="Treinamento Assíncrono",
    description="Envia treinamento para a fila Celery.",
    dependencies=[EngineeringRequired],
)
async def train_async(body: TrainRequest) -> APIResponse[dict]:
    from backend.workers.tasks.ml_tasks import task_train_model

    task = task_train_model.delay(
        model_type=body.model_type.value,
        target=body.target.value,
        transformer_ids=body.transformer_ids,
        date_start_iso=str(body.date_start) if body.date_start else None,
        date_end_iso=str(body.date_end) if body.date_end else None,
        n_estimators=body.n_estimators,
        max_depth=body.max_depth,
        learning_rate=body.learning_rate,
    )
    return APIResponse(
        data={"task_id": task.id, "status": "queued"},
        message="Treinamento enviado para a fila.",
    )


@router.post(
    "/predict/batch/async",
    summary="Predição em Lote Assíncrona",
    description="Envia predição em lote para a fila Celery.",
    dependencies=[EngineeringRequired],
)
async def predict_batch_async(body: BatchPredictRequest) -> APIResponse[dict]:
    from backend.workers.tasks.ml_tasks import task_predict_batch

    task = task_predict_batch.delay(
        transformer_ids=body.transformer_ids,
        ref_date_iso=str(body.ref_date),
        target=body.target.value,
    )
    return APIResponse(
        data={"task_id": task.id, "status": "queued"},
        message="Predição em lote enviada para a fila.",
    )
