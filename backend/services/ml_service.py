"""
MLService — orquestrador principal do Ato 7.
"""

from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Optional

import structlog
from sqlalchemy import and_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from backend.domain.ml_model import (
    ModelStatus,
    PredictionTarget,
    TrainingConfig,
    is_model_acceptable,
)
from backend.models.transformer_balance import TransformerBalance
from backend.repositories.ml_model_repository import MlModelRepository
from backend.schemas.ml import (
    BatchPredictionResponse,
    PredictionResponse,
    TrainResponse,
)
from backend.services.ml.feature_engineering import FeatureEngineer
from backend.services.ml.model_registry import ModelRegistry
from backend.services.ml.trainer import ModelTrainer

logger = structlog.get_logger(__name__)


class MlService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repo = MlModelRepository(session)
        self._registry = ModelRegistry(self._repo)
        self._feature_eng = FeatureEngineer(session)

    async def train(
        self,
        config: TrainingConfig,
        transformer_ids: Optional[list[str]] = None,
        date_start: Optional[date] = None,
        date_end: Optional[date] = None,
    ) -> TrainResponse:
        log = logger.bind(
            target=config.target.value,
            model_type=config.model_type.value,
        )
        log.info("ml_service.train.started")

        df = await self._feature_eng.build_training_dataset(
            transformer_ids=transformer_ids,
            date_start=date_start,
            date_end=date_end,
            target=config.target,
        )

        if df.empty or len(df) < 20:
            raise ValueError(
                f"Dados insuficientes para treinar: {len(df)} amostras "
                f"(mínimo 20 para {config.target.value})."
            )

        trainer = ModelTrainer(config)
        metrics, artifact, version = trainer.train(df)
        acceptable = is_model_acceptable(metrics, config.target)

        metrics_dict = {
            "mae": metrics.mae,
            "rmse": metrics.rmse,
            "r2": metrics.r2,
            "mape": metrics.mape,
            "cv_mean": metrics.cv_mean,
            "cv_std": metrics.cv_std,
            "n_train": metrics.n_train,
            "n_test": metrics.n_test,
            "feature_importances": metrics.feature_importances,
        }

        if acceptable:
            await self._registry.register(
                version=version,
                model_type=config.model_type,
                target=config.target,
                config=config,
                metrics_dict=metrics_dict,
                artifact=artifact,
            )
            status = ModelStatus.READY.value
        else:
            await self._repo.mark_failed(version)
            status = ModelStatus.FAILED.value
            log.warning(
                "ml_service.train.model_rejected",
                r2=metrics.r2,
                mape=metrics.mape,
            )

        await self._session.commit()

        return TrainResponse(
            version=version,
            status=status,
            model_type=config.model_type.value,
            target=config.target.value,
            acceptable=acceptable,
            metrics=metrics_dict,
            n_samples=len(df),
        )

    async def predict(
        self,
        transformer_id: str,
        ref_date: date,
        target: PredictionTarget,
        actual_value: Optional[float] = None,
    ) -> PredictionResponse:
        predictor = await self._registry.get_predictor(target)
        if not predictor:
            raise ValueError(
                f"Nenhum modelo ativo para target '{target.value}'. "
                "Treine um modelo primeiro via POST /ml/train."
            )

        balance = await self._session.scalar(
            select(TransformerBalance)
            .where(TransformerBalance.transformer_id == transformer_id)
            .order_by(TransformerBalance.period_start.desc())
        )
        if not balance:
            raise ValueError(
                f"Balanço não encontrado para {transformer_id} em {ref_date}."
            )

        from backend.models.climate_record import ClimateRecord
        from backend.repositories.climate_repository import ClimateRepository

        climate_repo = ClimateRepository(self._session)
        location = await climate_repo.get_transformer_location(transformer_id)
        climate = None

        if location:
            climate = await self._session.scalar(
                select(ClimateRecord).where(
                    and_(
                        ClimateRecord.latitude == round(location[0], 4),
                        ClimateRecord.longitude == round(location[1], 4),
                        ClimateRecord.ref_date == ref_date,
                    )
                )
            )

        feature_vector = await self._feature_eng.build_prediction_vector(
            transformer_id=transformer_id,
            ref_date=ref_date,
            balance=balance,
            climate=climate,
        )
        if feature_vector is None:
            raise ValueError(
                f"Não foi possível construir vetor de features para "
                f"{transformer_id} em {ref_date}."
            )

        result = predictor.predict(
            transformer_id=transformer_id,
            ref_date=str(ref_date),
            feature_vector=feature_vector,
            actual_value=actual_value,
        )

        await self._repo.save_prediction(
            transformer_id=transformer_id,
            ref_date=ref_date,
            target=target.value,
            predicted_value=result.predicted_value,
            ci_lower=result.confidence_interval_lower,
            ci_upper=result.confidence_interval_upper,
            model_version=result.model_version,
            feature_contributions=result.feature_contributions,
            is_anomaly=result.is_anomaly,
            anomaly_score=result.anomaly_score,
            actual_value=actual_value,
        )

        if target == PredictionTarget.ADJUSTED_BALANCE:
            await self._update_ml_adjusted(
                transformer_id, ref_date, result.predicted_value
            )

        await self._session.commit()

        return PredictionResponse(
            transformer_id=transformer_id,
            ref_date=str(ref_date),
            target=target.value,
            predicted_value=result.predicted_value,
            ci_lower=result.confidence_interval_lower,
            ci_upper=result.confidence_interval_upper,
            model_version=result.model_version,
            feature_contributions=result.feature_contributions,
            is_anomaly=result.is_anomaly,
            anomaly_score=result.anomaly_score,
        )

    async def predict_batch(
        self,
        transformer_ids: list[str],
        ref_date: date,
        target: PredictionTarget,
    ) -> BatchPredictionResponse:
        results = []
        errors = []

        for tid in transformer_ids:
            try:
                pred = await self.predict(
                    transformer_id=tid,
                    ref_date=ref_date,
                    target=target,
                )
                results.append(pred)
            except Exception as exc:
                errors.append({"transformer_id": tid, "error": str(exc)})
                logger.warning(
                    "ml_service.batch.transformer_failed",
                    transformer_id=tid,
                    error=str(exc),
                )

        anomalies = [r for r in results if r.is_anomaly]

        return BatchPredictionResponse(
            ref_date=str(ref_date),
            target=target.value,
            total=len(transformer_ids),
            success=len(results),
            failed=len(errors),
            anomalies_detected=len(anomalies),
            predictions=results,
            errors=errors,
        )

    async def get_anomalies(
        self, min_score: float = 2.0, limit: int = 100
    ) -> list[dict]:
        records = await self._repo.get_anomalies(min_score=min_score, limit=limit)
        return [
            {
                "transformer_id": r.transformer_id,
                "ref_date": str(r.ref_date),
                "target": r.target,
                "predicted_value": r.predicted_value,
                "actual_value": r.actual_value,
                "anomaly_score": r.anomaly_score,
                "model_version": r.model_version,
            }
            for r in records
        ]

    async def _update_ml_adjusted(
        self,
        transformer_id: str,
        ref_date: date,
        adjusted_value: float,
    ) -> None:
        await self._session.execute(
            update(TransformerBalance)
            .where(
                and_(
                    TransformerBalance.transformer_id == transformer_id,
                    TransformerBalance.period_start <= ref_date,
                    TransformerBalance.period_end >= ref_date,
                )
            )
            .values(
                ml_adjusted=adjusted_value,
                updated_at=datetime.now(timezone.utc),
            )
        )