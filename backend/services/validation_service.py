from datetime import datetime, timezone
from typing import Optional

import structlog
from sqlalchemy.orm import Session

from backend.repositories.calibration_repository import CalibrationRepository
from backend.repositories.validation_repository import AnomalyRepository, ValidationRepository
from backend.schemas.validation import (
    AnomalyDetectionRequest,
    AnomalyDetectionResponse,
    CalibrationRequest,
    CalibrationResponse,
    ValidationRequest,
    ValidationResponse,
)
from ml_engine.anomaly_detection.anomaly_service import (
    AnomalyDetectionService,
    EnergyFeatureVector,
)
from ml_engine.calibration.kwp_calibrator import KWpCalibrator
from ml_engine.calibration.loss_calibrator import LossCalibrator
from ml_engine.continuous_learning.feedback_collector import FeedbackCollector, FeedbackRecord
from ml_engine.continuous_learning.model_updater import ModelUpdater

logger = structlog.get_logger(__name__)


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class ValidationService:
    def __init__(self, db: Session):
        self._db = db
        self._validation_repo = ValidationRepository(db)
        self._anomaly_repo = AnomalyRepository(db)
        self._calibration_repo = CalibrationRepository(db)

    def validate_transformer(
        self, request: ValidationRequest
    ) -> ValidationResponse:
        logger.info(
            "validation_service.start",
            transformer_id=request.transformer_id,
            period=request.reference_period,
        )

        erro_absoluto = None
        erro_percentual = None
        desvio_sazonal = None
        status = "sem_medicao_real"

        if request.balanco_real_kwh is not None:
            erro_absoluto = abs(
                request.balanco_estimado_kwh - request.balanco_real_kwh
            )
            if request.balanco_real_kwh != 0:
                erro_percentual = round(
                    erro_absoluto / abs(request.balanco_real_kwh) * 100, 2
                )

            status = self._classify_status(erro_percentual)

        if request.balanco_real_kwh_sazonal is not None and request.balanco_real_kwh:
            desvio_sazonal = round(
                abs(request.balanco_real_kwh - request.balanco_real_kwh_sazonal)
                / abs(request.balanco_real_kwh)
                * 100
                if request.balanco_real_kwh != 0
                else 0.0,
                2,
            )

        score = self._calculate_score(erro_percentual, request.confianca_media)

        record_data = {
            "transformer_id": request.transformer_id,
            "reference_period": request.reference_period,
            "consumo_estimado_kwh": request.consumo_estimado_kwh,
            "geracao_estimada_kwh": request.geracao_estimada_kwh,
            "injecao_estimada_kwh": request.injecao_estimada_kwh,
            "balanco_estimado_kwh": request.balanco_estimado_kwh,
            "consumo_real_kwh": request.consumo_real_kwh,
            "geracao_real_kwh": request.geracao_real_kwh,
            "balanco_real_kwh": request.balanco_real_kwh,
            "erro_absoluto_kwh": round(erro_absoluto, 4) if erro_absoluto else None,
            "erro_percentual_pct": erro_percentual,
            "desvio_sazonal_pct": desvio_sazonal,
            "score_operacional": score,
            "status_validacao": status,
        }

        record = self._validation_repo.create_validation(record_data)

        logger.info(
            "validation_service.done",
            transformer_id=request.transformer_id,
            erro_percentual=erro_percentual,
            score=score,
            status=status,
        )

        return ValidationResponse(
            id=record.id,
            transformer_id=record.transformer_id,
            reference_period=record.reference_period,
            consumo_estimado_kwh=record.consumo_estimado_kwh,
            geracao_estimada_kwh=record.geracao_estimada_kwh,
            balanco_estimado_kwh=record.balanco_estimado_kwh,
            balanco_real_kwh=record.balanco_real_kwh,
            erro_absoluto_kwh=record.erro_absoluto_kwh,
            erro_percentual_pct=record.erro_percentual_pct,
            desvio_sazonal_pct=record.desvio_sazonal_pct,
            score_operacional=record.score_operacional,
            status_validacao=record.status_validacao,
            created_at=record.created_at,
        )

    def detect_anomaly(
        self, request: AnomalyDetectionRequest, db: Session
    ) -> AnomalyDetectionResponse:
        service = AnomalyDetectionService()

        features = EnergyFeatureVector(
            consumo_estimado_kwh=request.consumo_estimado_kwh,
            geracao_estimada_kwh=request.geracao_estimada_kwh,
            injecao_estimada_kwh=request.injecao_estimada_kwh,
            erro_balanco_pct=request.erro_balanco_pct,
            kwp_estimado=request.kwp_estimado,
            area_m2=request.area_m2,
            confianca_deteccao=request.confianca_deteccao,
        )

        result = service.detect(uc_code=request.uc_code, features=features)

        repo = AnomalyRepository(db)
        repo.create(
            {
                "uc_code": request.uc_code,
                "transformer_id": request.transformer_id,
                "is_anomaly": result.is_anomaly,
                "consensus": result.consensus,
                "isolation_forest_score": result.isolation_forest.score,
                "one_class_svm_score": result.one_class_svm.score,
                "final_score": result.final_score,
                "recommendation": result.recommendation,
                "features_json": result.features,
            }
        )

        return AnomalyDetectionResponse(
            uc_code=result.uc_code,
            transformer_id=request.transformer_id,
            is_anomaly=result.is_anomaly,
            consensus=result.consensus,
            final_score=result.final_score,
            recommendation=result.recommendation,
            isolation_forest_score=result.isolation_forest.score,
            one_class_svm_score=result.one_class_svm.score,
        )

    def run_calibration(
        self, request: CalibrationRequest, db: Session
    ) -> CalibrationResponse:
        kwp_calibrator = KWpCalibrator()
        loss_calibrator = LossCalibrator()
        feedback_collector = FeedbackCollector()

        for feedback in request.feedback_records:
            feedback_collector.add(
                FeedbackRecord(
                    uc_code=feedback.uc_code,
                    transformer_id=request.transformer_id,
                    timestamp=feedback.timestamp,
                    kwp_estimated=feedback.kwp_estimated,
                    kwp_real=feedback.kwp_real,
                    consumo_estimado_kwh=feedback.consumo_estimado_kwh,
                    consumo_real_kwh=feedback.consumo_real_kwh,
                    geracao_estimada_kwh=feedback.geracao_estimada_kwh,
                    geracao_real_kwh=feedback.geracao_real_kwh,
                    area_m2=feedback.area_m2,
                    confianca=feedback.confianca,
                    source=feedback.source,
                )
            )

        updater = ModelUpdater(kwp_calibrator, loss_calibrator, feedback_collector)

        cycle = updater.run_update_cycle(
            transformer_id=request.transformer_id,
            energy_injected_kwh=request.energy_injected_kwh,
            energy_measured_kwh=request.energy_measured_kwh,
        )

        if not cycle:
            return CalibrationResponse(
                transformer_id=request.transformer_id,
                executed_at=utc_now(),
                kwp_factor_old=kwp_calibrator.current_factor,
                kwp_factor_new=kwp_calibrator.current_factor,
                loss_factor_old=loss_calibrator.current_loss_factor,
                loss_factor_new=loss_calibrator.current_loss_factor,
                samples_used=0,
                mean_kwp_error_pct=0.0,
                converged=False,
                notes=["Amostras insuficientes para calibração"],
            )

        repo = CalibrationRepository(db)
        repo.create(
            {
                "transformer_id": request.transformer_id,
                "kwp_factor_old": cycle.kwp_factor_old,
                "kwp_factor_new": cycle.kwp_factor_new,
                "kwp_factor_delta": round(cycle.kwp_factor_new - cycle.kwp_factor_old, 6),
                "loss_factor_old": cycle.loss_factor_old,
                "loss_factor_new": cycle.loss_factor_new,
                "loss_factor_delta": round(
                    cycle.loss_factor_new - cycle.loss_factor_old, 6
                ),
                "samples_used": cycle.samples_used,
                "mean_kwp_error_pct": cycle.mean_kwp_error_pct,
                "mean_consumo_error_pct": cycle.mean_consumo_error_pct,
                "converged": cycle.converged,
                "notes": "\n".join(cycle.notes),
                "executed_at": cycle.executed_at,
            }
        )

        return CalibrationResponse(
            transformer_id=request.transformer_id,
            executed_at=cycle.executed_at,
            kwp_factor_old=cycle.kwp_factor_old,
            kwp_factor_new=cycle.kwp_factor_new,
            loss_factor_old=cycle.loss_factor_old,
            loss_factor_new=cycle.loss_factor_new,
            samples_used=cycle.samples_used,
            mean_kwp_error_pct=cycle.mean_kwp_error_pct,
            converged=cycle.converged,
            notes=cycle.notes,
        )

    def _classify_status(self, erro_pct: Optional[float]) -> str:
        if erro_pct is None:
            return "sem_medicao_real"
        if erro_pct <= 10.0:
            return "validado"
        if erro_pct <= 20.0:
            return "divergencia_moderada"
        if erro_pct <= 35.0:
            return "divergencia_alta"
        return "critico"

    def _calculate_score(
        self,
        erro_pct: Optional[float],
        confianca: float,
    ) -> str:
        if erro_pct is None:
            return "baixo_risco"
        if erro_pct <= 10.0 and confianca >= 0.75:
            return "baixo_risco"
        if erro_pct <= 20.0:
            return "medio_risco"
        if erro_pct <= 35.0:
            return "alto_risco"
        return "prioridade_inspecao"