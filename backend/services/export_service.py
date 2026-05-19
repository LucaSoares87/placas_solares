import csv
import io
from datetime import datetime, timezone
from typing import Optional

import structlog
from sqlalchemy.orm import Session

from backend.repositories.calibration_repository import CalibrationRepository
from backend.repositories.dashboard_repository import DashboardRepository
from backend.repositories.validation_repository import AnomalyRepository, ValidationRepository
from backend.schemas.dashboard import BIPayloadResponse, ExportRequest

logger = structlog.get_logger(__name__)


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class ExportService:
    def __init__(self, db: Session):
        self._db = db
        self._dash_repo = DashboardRepository(db)
        self._val_repo = ValidationRepository(db)
        self._anomaly_repo = AnomalyRepository(db)
        self._calib_repo = CalibrationRepository(db)

    def export_json(self, request: ExportRequest) -> dict:
        logger.info("export_service.json_start")
        snapshots = self._dash_repo.list_all_latest()

        if request.transformer_ids:
            snapshots = [
                snapshot
                for snapshot in snapshots
                if snapshot.transformer_id in request.transformer_ids
            ]

        result: dict = {
            "schema_version": "1.0",
            "exported_at": utc_now().isoformat(),
            "reference_period": request.reference_period,
            "total_transformers": len(snapshots),
            "transformers": [],
        }

        for snap in snapshots:
            entry: dict = {
                "transformer_id": snap.transformer_id,
                "reference_period": snap.reference_period,
                "kpis": {
                    "total_ucs": snap.total_ucs,
                    "total_ucs_fv": snap.total_ucs_fv,
                    "cobertura_fv_pct": snap.cobertura_fv_pct,
                    "kwp_total_estimado": snap.kwp_total_estimado,
                    "geracao_total_kwh": snap.geracao_total_kwh,
                    "consumo_total_kwh": snap.consumo_total_kwh,
                    "balanco_estimado_kwh": snap.balanco_estimado_kwh,
                    "balanco_real_kwh": snap.balanco_real_kwh,
                    "erro_balanco_pct": snap.erro_balanco_pct,
                },
                "risk": {
                    "score_operacional": snap.score_operacional,
                    "total_anomalias_ativas": snap.total_anomalias_ativas,
                    "total_inspecoes_pendentes": snap.total_inspecoes_pendentes,
                    "confianca_media": snap.confianca_media_deteccao,
                },
                "calibration": {
                    "kwp_factor_atual": snap.kwp_factor_atual,
                    "loss_factor_atual": snap.loss_factor_atual,
                    "modelo_convergido": snap.modelo_convergido,
                },
            }

            if request.include_validations:
                validations = self._val_repo.get_by_transformer(
                    snap.transformer_id, limit=12
                )
                entry["validations"] = [
                    {
                        "period": validation.reference_period,
                        "erro_percentual_pct": validation.erro_percentual_pct,
                        "status": validation.status_validacao,
                        "score": validation.score_operacional,
                    }
                    for validation in validations
                ]

            if request.include_anomalies:
                anomalies = self._anomaly_repo.get_active_by_transformer(
                    snap.transformer_id
                )
                entry["active_anomalies"] = [
                    {
                        "uc_code": anomaly.uc_code,
                        "is_anomaly": anomaly.is_anomaly,
                        "consensus": anomaly.consensus,
                        "final_score": anomaly.final_score,
                        "recommendation": anomaly.recommendation,
                        "detected_at": anomaly.detected_at.isoformat(),
                    }
                    for anomaly in anomalies
                ]

            if request.include_calibration:
                latest_calib = self._calib_repo.get_latest(snap.transformer_id)
                entry["latest_calibration"] = (
                    {
                        "kwp_factor_new": latest_calib.kwp_factor_new,
                        "loss_factor_new": latest_calib.loss_factor_new,
                        "converged": latest_calib.converged,
                        "mean_kwp_error_pct": latest_calib.mean_kwp_error_pct,
                        "samples_used": latest_calib.samples_used,
                        "executed_at": latest_calib.executed_at.isoformat(),
                    }
                    if latest_calib
                    else None
                )

            result["transformers"].append(entry)

        logger.info("export_service.json_done", transformers=len(snapshots))
        return result

    def export_csv(self, request: ExportRequest) -> str:
        logger.info("export_service.csv_start")
        data = self.export_json(request)

        output = io.StringIO()
        fieldnames = [
            "transformer_id",
            "reference_period",
            "total_ucs",
            "total_ucs_fv",
            "cobertura_fv_pct",
            "kwp_total_estimado",
            "geracao_total_kwh",
            "consumo_total_kwh",
            "balanco_estimado_kwh",
            "balanco_real_kwh",
            "erro_balanco_pct",
            "score_operacional",
            "total_anomalias_ativas",
            "total_inspecoes_pendentes",
            "confianca_media",
            "kwp_factor_atual",
            "loss_factor_atual",
            "modelo_convergido",
        ]

        writer = csv.DictWriter(
            output,
            fieldnames=fieldnames,
            extrasaction="ignore",
        )
        writer.writeheader()

        for transformer in data["transformers"]:
            row = {
                "transformer_id": transformer["transformer_id"],
                "reference_period": transformer["reference_period"],
                **transformer["kpis"],
                **transformer["risk"],
                **transformer["calibration"],
            }
            writer.writerow(row)

        csv_content = output.getvalue()
        output.close()

        logger.info("export_service.csv_done", rows=len(data["transformers"]))
        return csv_content

    def export_bi_payload(
        self, transformer_ids: Optional[list[str]] = None
    ) -> BIPayloadResponse:
        logger.info("export_service.bi_payload_start")

        kpis = self._dash_repo.get_global_kpis()
        snapshots = self._dash_repo.list_all_latest()

        if transformer_ids:
            snapshots = [
                snapshot
                for snapshot in snapshots
                if snapshot.transformer_id in transformer_ids
            ]

        transformers_payload = [
            {
                "transformer_id": snapshot.transformer_id,
                "reference_period": snapshot.reference_period,
                "score_operacional": snapshot.score_operacional,
                "total_ucs": snapshot.total_ucs,
                "total_ucs_fv": snapshot.total_ucs_fv,
                "cobertura_fv_pct": snapshot.cobertura_fv_pct,
                "kwp_total_estimado": snapshot.kwp_total_estimado,
                "geracao_total_kwh": snapshot.geracao_total_kwh,
                "consumo_total_kwh": snapshot.consumo_total_kwh,
                "erro_balanco_pct": snapshot.erro_balanco_pct,
                "total_anomalias_ativas": snapshot.total_anomalias_ativas,
                "modelo_convergido": snapshot.modelo_convergido,
                "kwp_factor_atual": snapshot.kwp_factor_atual,
                "loss_factor_atual": snapshot.loss_factor_atual,
                "gerado_em": snapshot.gerado_em.isoformat(),
            }
            for snapshot in snapshots
        ]

        anomalies_summary = [
            {
                "transformer_id": snapshot.transformer_id,
                "total_anomalias_ativas": snapshot.total_anomalias_ativas,
                "score_operacional": snapshot.score_operacional,
                "reference_period": snapshot.reference_period,
            }
            for snapshot in snapshots
            if (snapshot.total_anomalias_ativas or 0) > 0
        ]

        calibration_summary = []
        for snapshot in snapshots:
            calib = self._calib_repo.get_latest(snapshot.transformer_id)
            if calib:
                calibration_summary.append(
                    {
                        "transformer_id": snapshot.transformer_id,
                        "kwp_factor_new": calib.kwp_factor_new,
                        "loss_factor_new": calib.loss_factor_new,
                        "converged": calib.converged,
                        "mean_kwp_error_pct": calib.mean_kwp_error_pct,
                        "samples_used": calib.samples_used,
                        "executed_at": calib.executed_at.isoformat(),
                    }
                )

        logger.info(
            "export_service.bi_payload_done",
            transformers=len(transformers_payload),
        )

        return BIPayloadResponse(
            kpis=kpis,
            transformers=transformers_payload,
            anomalies_summary=anomalies_summary,
            calibration_summary=calibration_summary,
        )