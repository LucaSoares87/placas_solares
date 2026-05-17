"""
Repositório para modelos ML e predições.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

import structlog
from sqlalchemy import and_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.ml_model_record import MlModelRecord
from backend.models.ml_prediction import MlPrediction

logger = structlog.get_logger(__name__)


class MlModelRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    # ─────────────────────────────────────────────────────────────────────────
    # Modelos
    # ─────────────────────────────────────────────────────────────────────────

    async def save_model(
        self,
        version: str,
        model_type: str,
        target: str,
        status: str,
        config_json: dict,
        metrics_json: dict,
        artifact: bytes,
    ) -> str:
        now = datetime.now(timezone.utc)
        record = MlModelRecord(
            version=version,
            model_type=model_type,
            target=target,
            status=status,
            config_json=config_json,
            metrics_json=metrics_json,
            artifact=artifact,
            created_at=now,
            updated_at=now,
        )
        self._session.add(record)
        await self._session.flush()
        logger.info("ml_repo.model_saved", version=version, target=target)
        return version

    async def get_active_model(self, target: str) -> Optional[MlModelRecord]:
        return await self._session.scalar(
            select(MlModelRecord).where(
                and_(
                    MlModelRecord.target == target,
                    MlModelRecord.status == "ready",
                )
            ).order_by(MlModelRecord.created_at.desc())
        )

    async def deprecate_active(self, target: str) -> None:
        await self._session.execute(
            update(MlModelRecord)
            .where(
                and_(
                    MlModelRecord.target == target,
                    MlModelRecord.status == "ready",
                )
            )
            .values(status="deprecated", updated_at=datetime.now(timezone.utc))
        )

    async def list_versions(self, target: str) -> list[dict]:
        result = await self._session.execute(
            select(MlModelRecord)
            .where(MlModelRecord.target == target)
            .order_by(MlModelRecord.created_at.desc())
        )
        records = result.scalars().all()
        return [
            {
                "version": r.version,
                "model_type": r.model_type,
                "status": r.status,
                "metrics": r.metrics_json,
                "created_at": str(r.created_at),
            }
            for r in records
        ]

    async def mark_failed(self, version: str) -> None:
        await self._session.execute(
            update(MlModelRecord)
            .where(MlModelRecord.version == version)
            .values(status="failed", updated_at=datetime.now(timezone.utc))
        )

    # ─────────────────────────────────────────────────────────────────────────
    # Predições
    # ─────────────────────────────────────────────────────────────────────────

    async def save_prediction(
        self,
        transformer_id: str,
        ref_date,
        target: str,
        predicted_value: float,
        ci_lower: float,
        ci_upper: float,
        model_version: str,
        feature_contributions: dict,
        is_anomaly: bool,
        anomaly_score: float,
        actual_value: Optional[float] = None,
    ) -> None:
        pred = MlPrediction(
            transformer_id=transformer_id,
            ref_date=ref_date,
            target=target,
            predicted_value=predicted_value,
            ci_lower=ci_lower,
            ci_upper=ci_upper,
            model_version=model_version,
            feature_contributions=feature_contributions,
            is_anomaly=is_anomaly,
            anomaly_score=anomaly_score,
            actual_value=actual_value,
            created_at=datetime.now(timezone.utc),
        )
        self._session.add(pred)
        await self._session.flush()

    async def get_predictions_for_transformer(
        self,
        transformer_id: str,
        target: str,
        limit: int = 30,
    ) -> list[MlPrediction]:
        result = await self._session.execute(
            select(MlPrediction)
            .where(
                and_(
                    MlPrediction.transformer_id == transformer_id,
                    MlPrediction.target == target,
                )
            )
            .order_by(MlPrediction.ref_date.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_anomalies(
        self, min_score: float = 2.0, limit: int = 100
    ) -> list[MlPrediction]:
        result = await self._session.execute(
            select(MlPrediction)
            .where(
                and_(
                    MlPrediction.is_anomaly.is_(True),
                    MlPrediction.anomaly_score >= min_score,
                )
            )
            .order_by(MlPrediction.anomaly_score.desc())
            .limit(limit)
        )
        return list(result.scalars().all())
