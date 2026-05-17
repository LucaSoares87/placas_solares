import structlog
from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import desc

from backend.models.calibration import CalibrationHistory

logger = structlog.get_logger(__name__)


class CalibrationRepository:
    def __init__(self, db: Session):
        self._db = db

    def create(self, data: dict) -> CalibrationHistory:
        record = CalibrationHistory(**data)
        self._db.add(record)
        self._db.commit()
        self._db.refresh(record)
        logger.info(
            "calibration_repo.created",
            transformer_id=record.transformer_id,
            kwp_new=record.kwp_factor_new,
            converged=record.converged,
        )
        return record

    def get_latest(self, transformer_id: str) -> Optional[CalibrationHistory]:
        return (
            self._db.query(CalibrationHistory)
            .filter(CalibrationHistory.transformer_id == transformer_id)
            .order_by(desc(CalibrationHistory.executed_at))
            .first()
        )

    def get_history(
        self,
        transformer_id: str,
        limit: int = 30,
    ) -> list[CalibrationHistory]:
        return (
            self._db.query(CalibrationHistory)
            .filter(CalibrationHistory.transformer_id == transformer_id)
            .order_by(desc(CalibrationHistory.executed_at))
            .limit(limit)
            .all()
        )

    def get_converged_transformers(self) -> list[str]:
        records = (
            self._db.query(CalibrationHistory.transformer_id)
            .filter(CalibrationHistory.converged.is_(True))
            .distinct()
            .all()
        )
        return [r[0] for r in records]
