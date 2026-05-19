from datetime import datetime, timedelta, timezone
from typing import Optional

import structlog
from sqlalchemy import and_, desc, func
from sqlalchemy.orm import Session

from backend.models.calibration import CalibrationHistory
from backend.models.dashboard import AlertRecord, DashboardSnapshot
from backend.models.validation import AnomalyRecord, ValidationRecord

logger = structlog.get_logger(__name__)


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class DashboardRepository:
    def __init__(self, db: Session):
        self._db = db

    def upsert_snapshot(self, data: dict) -> DashboardSnapshot:
        existing = (
            self._db.query(DashboardSnapshot)
            .filter(
                DashboardSnapshot.transformer_id == data["transformer_id"],
                DashboardSnapshot.reference_period == data["reference_period"],
            )
            .first()
        )

        if existing:
            for key, value in data.items():
                setattr(existing, key, value)

            existing.gerado_em = utc_now()
            self._db.commit()
            self._db.refresh(existing)
            return existing

        snapshot = DashboardSnapshot(**data)
        self._db.add(snapshot)
        self._db.commit()
        self._db.refresh(snapshot)
        logger.info(
            "dashboard_repo.snapshot_created",
            transformer_id=snapshot.transformer_id,
            period=snapshot.reference_period,
        )
        return snapshot

    def get_latest_snapshot(
        self, transformer_id: str
    ) -> Optional[DashboardSnapshot]:
        return (
            self._db.query(DashboardSnapshot)
            .filter(DashboardSnapshot.transformer_id == transformer_id)
            .order_by(desc(DashboardSnapshot.gerado_em))
            .first()
        )

    def get_snapshot_history(
        self, transformer_id: str, limit: int = 12
    ) -> list[DashboardSnapshot]:
        return (
            self._db.query(DashboardSnapshot)
            .filter(DashboardSnapshot.transformer_id == transformer_id)
            .order_by(desc(DashboardSnapshot.gerado_em))
            .limit(limit)
            .all()
        )

    def list_all_latest(self) -> list[DashboardSnapshot]:
        subq = (
            self._db.query(
                DashboardSnapshot.transformer_id,
                func.max(DashboardSnapshot.gerado_em).label("max_ts"),
            )
            .group_by(DashboardSnapshot.transformer_id)
            .subquery()
        )
        return (
            self._db.query(DashboardSnapshot)
            .join(
                subq,
                and_(
                    DashboardSnapshot.transformer_id == subq.c.transformer_id,
                    DashboardSnapshot.gerado_em == subq.c.max_ts,
                ),
            )
            .all()
        )

    def get_risk_ranking(self, limit: int = 50) -> list[dict]:
        score_order = {
            "prioridade_inspecao": 4,
            "alto_risco": 3,
            "medio_risco": 2,
            "baixo_risco": 1,
        }

        snapshots = self.list_all_latest()
        ranked = sorted(
            snapshots,
            key=lambda s: (
                score_order.get(s.score_operacional, 0),
                s.erro_balanco_pct or 0.0,
                s.total_anomalias_ativas or 0,
            ),
            reverse=True,
        )

        return [
            {
                "rank": idx + 1,
                "transformer_id": s.transformer_id,
                "score_operacional": s.score_operacional,
                "erro_balanco_pct": s.erro_balanco_pct,
                "total_anomalias_ativas": s.total_anomalias_ativas,
                "kwp_total_estimado": s.kwp_total_estimado,
                "total_ucs_fv": s.total_ucs_fv,
                "confianca_media": s.confianca_media_deteccao,
                "reference_period": s.reference_period,
            }
            for idx, s in enumerate(ranked[:limit])
        ]

    def get_error_series(
        self, transformer_id: str, limit: int = 24
    ) -> list[dict]:
        records = (
            self._db.query(ValidationRecord)
            .filter(ValidationRecord.transformer_id == transformer_id)
            .order_by(desc(ValidationRecord.created_at))
            .limit(limit)
            .all()
        )
        return [
            {
                "period": r.reference_period,
                "erro_percentual_pct": r.erro_percentual_pct,
                "erro_absoluto_kwh": r.erro_absoluto_kwh,
                "score_operacional": r.score_operacional,
                "status_validacao": r.status_validacao,
                "created_at": r.created_at.isoformat(),
            }
            for r in reversed(records)
        ]

    def get_kwp_calibration_series(
        self, transformer_id: str, limit: int = 24
    ) -> list[dict]:
        records = (
            self._db.query(CalibrationHistory)
            .filter(CalibrationHistory.transformer_id == transformer_id)
            .order_by(desc(CalibrationHistory.executed_at))
            .limit(limit)
            .all()
        )
        return [
            {
                "executed_at": r.executed_at.isoformat(),
                "kwp_factor_old": r.kwp_factor_old,
                "kwp_factor_new": r.kwp_factor_new,
                "kwp_factor_delta": r.kwp_factor_delta,
                "loss_factor_new": r.loss_factor_new,
                "mean_kwp_error_pct": r.mean_kwp_error_pct,
                "converged": r.converged,
                "samples_used": r.samples_used,
            }
            for r in reversed(records)
        ]

    def get_anomaly_series(
        self, transformer_id: str, days: int = 90
    ) -> list[dict]:
        since = utc_now() - timedelta(days=days)
        records = (
            self._db.query(AnomalyRecord)
            .filter(
                AnomalyRecord.transformer_id == transformer_id,
                AnomalyRecord.detected_at >= since,
            )
            .order_by(AnomalyRecord.detected_at)
            .all()
        )
        return [
            {
                "uc_code": r.uc_code,
                "is_anomaly": r.is_anomaly,
                "consensus": r.consensus,
                "final_score": r.final_score,
                "recommendation": r.recommendation,
                "detected_at": r.detected_at.isoformat(),
                "resolved": r.resolved_at is not None,
            }
            for r in records
        ]

    def get_map_data(self) -> list[dict]:
        snapshots = self.list_all_latest()
        return [
            {
                "transformer_id": s.transformer_id,
                "score_operacional": s.score_operacional,
                "kwp_total_estimado": s.kwp_total_estimado,
                "total_ucs_fv": s.total_ucs_fv,
                "erro_balanco_pct": s.erro_balanco_pct,
                "total_anomalias_ativas": s.total_anomalias_ativas,
                "reference_period": s.reference_period,
                "coordinates": (
                    s.snapshot_metadata.get("coordinates")
                    if s.snapshot_metadata
                    else None
                ),
            }
            for s in snapshots
        ]

    def get_global_kpis(self) -> dict:
        snapshots = self.list_all_latest()

        if not snapshots:
            return {
                "total_transformadores": 0,
                "total_ucs": 0,
                "total_ucs_fv": 0,
                "cobertura_fv_pct": 0.0,
                "kwp_total": 0.0,
                "geracao_total_kwh": 0.0,
                "consumo_total_kwh": 0.0,
                "erro_medio_balanco_pct": 0.0,
                "total_anomalias_ativas": 0,
                "transformadores_criticos": 0,
            }

        total_ucs = sum(s.total_ucs or 0 for s in snapshots)
        total_fv = sum(s.total_ucs_fv or 0 for s in snapshots)
        kwp_total = sum(s.kwp_total_estimado or 0.0 for s in snapshots)
        geracao = sum(s.geracao_total_kwh or 0.0 for s in snapshots)
        consumo = sum(s.consumo_total_kwh or 0.0 for s in snapshots)
        anomalias = sum(s.total_anomalias_ativas or 0 for s in snapshots)
        criticos = sum(
            1
            for s in snapshots
            if s.score_operacional in ("alto_risco", "prioridade_inspecao")
        )

        erros = [
            s.erro_balanco_pct
            for s in snapshots
            if s.erro_balanco_pct is not None
        ]
        erro_medio = round(sum(erros) / len(erros), 2) if erros else 0.0
        cobertura = round(total_fv / total_ucs * 100, 1) if total_ucs > 0 else 0.0

        return {
            "total_transformadores": len(snapshots),
            "total_ucs": total_ucs,
            "total_ucs_fv": total_fv,
            "cobertura_fv_pct": cobertura,
            "kwp_total": round(kwp_total, 2),
            "geracao_total_kwh": round(geracao, 2),
            "consumo_total_kwh": round(consumo, 2),
            "erro_medio_balanco_pct": erro_medio,
            "total_anomalias_ativas": anomalias,
            "transformadores_criticos": criticos,
        }


class AlertRepository:
    def __init__(self, db: Session):
        self._db = db

    def create(self, data: dict) -> AlertRecord:
        record = AlertRecord(**data)
        self._db.add(record)
        self._db.commit()
        self._db.refresh(record)
        logger.info(
            "alert_repo.created",
            transformer_id=record.transformer_id,
            alert_type=record.alert_type,
            severity=record.severity,
        )
        return record

    def list_open(
        self,
        transformer_id: Optional[str] = None,
        severity: Optional[str] = None,
        limit: int = 100,
    ) -> list[AlertRecord]:
        q = self._db.query(AlertRecord).filter(AlertRecord.status == "aberto")
        if transformer_id:
            q = q.filter(AlertRecord.transformer_id == transformer_id)
        if severity:
            q = q.filter(AlertRecord.severity == severity)
        return q.order_by(desc(AlertRecord.created_at)).limit(limit).all()

    def acknowledge(
        self,
        alert_id: int,
        acknowledged_by: str,
    ) -> Optional[AlertRecord]:
        record = self._db.query(AlertRecord).filter(
            AlertRecord.id == alert_id
        ).first()
        if not record:
            return None

        record.status = "reconhecido"
        record.acknowledged_by = acknowledged_by
        record.acknowledged_at = utc_now()

        self._db.commit()
        self._db.refresh(record)
        return record

    def resolve(
        self,
        alert_id: int,
        notes: Optional[str] = None,
    ) -> Optional[AlertRecord]:
        record = self._db.query(AlertRecord).filter(
            AlertRecord.id == alert_id
        ).first()
        if not record:
            return None

        record.status = "resolvido"
        record.resolved_at = utc_now()
        record.resolution_notes = notes

        self._db.commit()
        self._db.refresh(record)
        return record

    def count_open_by_severity(self, transformer_id: str) -> dict:
        rows = (
            self._db.query(AlertRecord.severity, func.count(AlertRecord.id))
            .filter(
                AlertRecord.transformer_id == transformer_id,
                AlertRecord.status == "aberto",
            )
            .group_by(AlertRecord.severity)
            .all()
        )
        return {severity: count for severity, count in rows}