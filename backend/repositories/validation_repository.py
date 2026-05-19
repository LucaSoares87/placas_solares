from datetime import datetime, timezone
from typing import Optional

import structlog
from sqlalchemy import desc
from sqlalchemy.orm import Session

from backend.models.validation import AnomalyRecord, ValidationRecord

logger = structlog.get_logger(__name__)


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class ValidationRepository:
    def __init__(self, db: Session):
        self._db = db

    def create_validation(self, data: dict) -> ValidationRecord:
        record = ValidationRecord(**data)
        self._db.add(record)
        self._db.commit()
        self._db.refresh(record)
        logger.info(
            "validation_repo.created",
            transformer_id=record.transformer_id,
            period=record.reference_period,
        )
        return record

    def get_by_transformer(
        self,
        transformer_id: str,
        limit: int = 50,
    ) -> list[ValidationRecord]:
        return (
            self._db.query(ValidationRecord)
            .filter(ValidationRecord.transformer_id == transformer_id)
            .order_by(desc(ValidationRecord.created_at))
            .limit(limit)
            .all()
        )

    def get_by_period(
        self,
        transformer_id: str,
        reference_period: str,
    ) -> Optional[ValidationRecord]:
        return (
            self._db.query(ValidationRecord)
            .filter(
                ValidationRecord.transformer_id == transformer_id,
                ValidationRecord.reference_period == reference_period,
            )
            .first()
        )

    def update_status(
        self, record_id: int, status: str, observacoes: Optional[str] = None
    ) -> Optional[ValidationRecord]:
        record = (
            self._db.query(ValidationRecord)
            .filter(ValidationRecord.id == record_id)
            .first()
        )
        if not record:
            return None

        record.status_validacao = status
        if observacoes:
            record.observacoes = observacoes

        self._db.commit()
        self._db.refresh(record)
        return record

    def list_pending(self, limit: int = 100) -> list[ValidationRecord]:
        return (
            self._db.query(ValidationRecord)
            .filter(ValidationRecord.status_validacao == "pendente")
            .order_by(desc(ValidationRecord.created_at))
            .limit(limit)
            .all()
        )


class AnomalyRepository:
    def __init__(self, db: Session):
        self._db = db

    def create(self, data: dict) -> AnomalyRecord:
        record = AnomalyRecord(**data)
        self._db.add(record)
        self._db.commit()
        self._db.refresh(record)
        logger.info(
            "anomaly_repo.created",
            uc_code=record.uc_code,
            is_anomaly=record.is_anomaly,
        )
        return record

    def get_active_by_transformer(
        self, transformer_id: str
    ) -> list[AnomalyRecord]:
        return (
            self._db.query(AnomalyRecord)
            .filter(
                AnomalyRecord.transformer_id == transformer_id,
                AnomalyRecord.resolved_at.is_(None),
            )
            .order_by(desc(AnomalyRecord.detected_at))
            .all()
        )

    def resolve(
        self,
        record_id: int,
        resolved_by: str,
        notes: Optional[str] = None,
    ) -> Optional[AnomalyRecord]:
        record = (
            self._db.query(AnomalyRecord)
            .filter(AnomalyRecord.id == record_id)
            .first()
        )
        if not record:
            return None

        record.resolved_at = utc_now()
        record.resolved_by = resolved_by
        record.resolution_notes = notes

        self._db.commit()
        self._db.refresh(record)
        return record

    def get_unresolved_count(self, transformer_id: str) -> int:
        return (
            self._db.query(AnomalyRecord)
            .filter(
                AnomalyRecord.transformer_id == transformer_id,
                AnomalyRecord.resolved_at.is_(None),
                AnomalyRecord.is_anomaly.is_(True),
            )
            .count()
        )