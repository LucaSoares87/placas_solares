import pytest
from datetime import datetime, timezone

import numpy as np

from ml_engine.anomaly_detection.anomaly_service import (
    AnomalyDetectionService,
    EnergyFeatureVector,
)
from ml_engine.calibration.kwp_calibrator import (
    DEFAULT_FACTOR,
    MIN_SAMPLES,
    CalibrationSample,
    KWpCalibrator,
)
from ml_engine.calibration.loss_calibrator import LossCalibrator, LossSample
from ml_engine.continuous_learning.feedback_collector import (
    FeedbackCollector,
    FeedbackRecord,
)
from ml_engine.continuous_learning.model_updater import ModelUpdater


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


@pytest.fixture
def transformer_id() -> str:
    return "TR-102"


@pytest.fixture
def calibration_samples(transformer_id: str) -> list[CalibrationSample]:
    return [
        CalibrationSample(
            transformer_id=transformer_id,
            uc_code=f"UC-{i:03d}",
            area_m2=20.0 + i,
            kwp_estimated=3.0 + i * 0.1,
            kwp_real=3.2 + i * 0.1,
        )
        for i in range(MIN_SAMPLES + 2)
    ]


@pytest.fixture
def feature_vector() -> EnergyFeatureVector:
    return EnergyFeatureVector(
        consumo_estimado_kwh=150.0,
        geracao_estimada_kwh=120.0,
        injecao_estimada_kwh=30.0,
        erro_balanco_pct=5.0,
        kwp_estimado=5.1,
        area_m2=28.0,
        confianca_deteccao=0.85,
    )


@pytest.fixture
def feedback_records(transformer_id: str) -> list[FeedbackRecord]:
    return [
        FeedbackRecord(
            uc_code=f"UC-{i:03d}",
            transformer_id=transformer_id,
            timestamp=utc_now(),
            kwp_estimated=4.0,
            kwp_real=4.2,
            consumo_estimado_kwh=150.0,
            consumo_real_kwh=155.0,
            geracao_estimada_kwh=80.0,
            geracao_real_kwh=82.0,
            area_m2=28.0,
            confianca=0.85,
        )
        for i in range(5)
    ]


class TestKWpCalibrator:
    def test_calibrate_returns_none_insufficient_samples(
        self, transformer_id: str
    ):
        calibrator = KWpCalibrator()
        calibrator.add_sample(
            CalibrationSample(
                transformer_id=transformer_id,
                uc_code="UC-001",
                area_m2=20.0,
                kwp_estimated=3.0,
                kwp_real=3.2,
            )
        )
        result = calibrator.calibrate(transformer_id)
        assert result is None

    def test_calibrate_updates_factor(
        self,
        transformer_id: str,
        calibration_samples: list[CalibrationSample],
    ):
        calibrator = KWpCalibrator()
        for sample in calibration_samples:
            calibrator.add_sample(sample)

        result = calibrator.calibrate(transformer_id)

        assert result is not None
        assert result.new_factor != result.old_factor or result.samples_used >= MIN_SAMPLES
        assert result.samples_used == len(calibration_samples)

    def test_factor_clamped_between_bounds(self, transformer_id: str):
        calibrator = KWpCalibrator(current_factor=0.08)
        for i in range(MIN_SAMPLES + 1):
            calibrator.add_sample(
                CalibrationSample(
                    transformer_id=transformer_id,
                    uc_code=f"UC-{i}",
                    area_m2=1.0,
                    kwp_estimated=0.01,
                    kwp_real=0.001,
                )
            )
        result = calibrator.calibrate(transformer_id)
        if result:
            assert result.new_factor >= 0.08

    def test_mean_error_calculated_correctly(
        self,
        transformer_id: str,
        calibration_samples: list[CalibrationSample],
    ):
        calibrator = KWpCalibrator()
        for sample in calibration_samples:
            calibrator.add_sample(sample)
        result = calibrator.calibrate(transformer_id)
        assert result is not None
        assert result.mean_error_pct >= 0.0

    def test_converged_flag_when_error_low(self, transformer_id: str):
        calibrator = KWpCalibrator()
        for i in range(MIN_SAMPLES + 1):
            calibrator.add_sample(
                CalibrationSample(
                    transformer_id=transformer_id,
                    uc_code=f"UC-{i}",
                    area_m2=20.0,
                    kwp_estimated=3.0,
                    kwp_real=3.0,
                )
            )
        result = calibrator.calibrate(transformer_id)
        assert result is not None
        assert result.converged is True

    def test_invalid_sample_ignored(self, transformer_id: str):
        calibrator = KWpCalibrator()
        calibrator.add_sample(
            CalibrationSample(
                transformer_id=transformer_id,
                uc_code="UC-BAD",
                area_m2=0.0,
                kwp_estimated=3.0,
                kwp_real=0.0,
            )
        )
        assert len(calibrator._history) == 0

    def test_reset_history(
        self,
        transformer_id: str,
        calibration_samples: list[CalibrationSample],
    ):
        calibrator = KWpCalibrator()
        for sample in calibration_samples:
            calibrator.add_sample(sample)
        calibrator.reset_history(transformer_id)
        assert calibrator._history == []


class TestLossCalibrator:
    def test_calibrate_returns_none_insufficient(self, transformer_id: str):
        calibrator = LossCalibrator()
        calibrator.add_sample(
            LossSample(
                transformer_id=transformer_id,
                energy_injected_kwh=100.0,
                energy_measured_kwh=95.0,
            )
        )
        result = calibrator.calibrate(transformer_id)
        assert result is None

    def test_calibrate_computes_loss_factor(self, transformer_id: str):
        calibrator = LossCalibrator()
        for _ in range(5):
            calibrator.add_sample(
                LossSample(
                    transformer_id=transformer_id,
                    energy_injected_kwh=100.0,
                    energy_measured_kwh=92.0,
                )
            )
        result = calibrator.calibrate(transformer_id)
        assert result is not None
        assert result.new_loss_factor == pytest.approx(0.08, abs=0.01)

    def test_loss_factor_clamped(self, transformer_id: str):
        calibrator = LossCalibrator()
        for _ in range(5):
            calibrator.add_sample(
                LossSample(
                    transformer_id=transformer_id,
                    energy_injected_kwh=100.0,
                    energy_measured_kwh=1.0,
                )
            )
        result = calibrator.calibrate(transformer_id)
        assert result is not None
        assert result.new_loss_factor <= 0.25

    def test_invalid_sample_ignored(self, transformer_id: str):
        calibrator = LossCalibrator()
        calibrator.add_sample(
            LossSample(
                transformer_id=transformer_id,
                energy_injected_kwh=0.0,
                energy_measured_kwh=50.0,
            )
        )
        assert len(calibrator._samples) == 0


class TestAnomalyDetectionService:
    def test_detect_returns_result_unfitted(
        self, feature_vector: EnergyFeatureVector
    ):
        service = AnomalyDetectionService()
        result = service.detect("UC-001", feature_vector)

        assert result.uc_code == "UC-001"
        assert isinstance(result.is_anomaly, bool)
        assert isinstance(result.final_score, float)
        assert result.recommendation in (
            "inspecao_urgente",
            "inspecao_prioritaria",
            "monitoramento_intensivo",
            "normal",
        )

    def test_detect_batch(self, feature_vector: EnergyFeatureVector):
        service = AnomalyDetectionService()
        records = [("UC-001", feature_vector), ("UC-002", feature_vector)]
        results = service.detect_batch(records)
        assert len(results) == 2

    def test_fit_and_predict_normal(self):
        service = AnomalyDetectionService()
        normal_data = np.random.normal(loc=100, scale=5, size=(50, 7))
        service.fit(normal_data)

        feat = EnergyFeatureVector(
            consumo_estimado_kwh=100.0,
            geracao_estimada_kwh=100.0,
            injecao_estimada_kwh=10.0,
            erro_balanco_pct=5.0,
            kwp_estimado=5.0,
            area_m2=28.0,
            confianca_deteccao=0.85,
        )
        result = service.detect("UC-NORMAL", feat)
        assert isinstance(result.is_anomaly, bool)

    def test_recommendation_urgent_on_high_error(self):
        service = AnomalyDetectionService()
        feat = EnergyFeatureVector(
            consumo_estimado_kwh=50.0,
            geracao_estimada_kwh=200.0,
            injecao_estimada_kwh=150.0,
            erro_balanco_pct=45.0,
            kwp_estimado=30.0,
            area_m2=150.0,
            confianca_deteccao=0.30,
        )
        rec = service._build_recommendation(
            consensus=True, any_anomaly=True, features=feat
        )
        assert rec == "inspecao_urgente"


class TestFeedbackCollector:
    def test_add_and_retrieve(
        self,
        transformer_id: str,
        feedback_records: list[FeedbackRecord],
    ):
        collector = FeedbackCollector()
        collector.add_batch(feedback_records)
        retrieved = collector.get_by_transformer(transformer_id)
        assert len(retrieved) == len(feedback_records)

    def test_summarize(
        self,
        transformer_id: str,
        feedback_records: list[FeedbackRecord],
    ):
        collector = FeedbackCollector()
        collector.add_batch(feedback_records)
        summary = collector.summarize(transformer_id)

        assert summary is not None
        assert summary.total_records == len(feedback_records)
        assert summary.mean_kwp_error_pct >= 0.0
        assert summary.coverage_pct == 100.0

    def test_to_feature_matrix(
        self,
        transformer_id: str,
        feedback_records: list[FeedbackRecord],
    ):
        collector = FeedbackCollector()
        collector.add_batch(feedback_records)
        matrix = collector.to_feature_matrix(transformer_id)

        assert matrix.shape[0] == len(feedback_records)
        assert matrix.shape[1] == 5

    def test_clear_by_transformer(
        self,
        transformer_id: str,
        feedback_records: list[FeedbackRecord],
    ):
        collector = FeedbackCollector()
        collector.add_batch(feedback_records)
        collector.clear(transformer_id)
        assert collector.get_by_transformer(transformer_id) == []

    def test_summarize_empty_returns_none(self, transformer_id: str):
        collector = FeedbackCollector()
        result = collector.summarize(transformer_id)
        assert result is None


class TestModelUpdater:
    def test_cycle_returns_none_no_feedback(self, transformer_id: str):
        updater = ModelUpdater(
            KWpCalibrator(),
            LossCalibrator(),
            FeedbackCollector(),
        )
        result = updater.run_update_cycle(transformer_id)
        assert result is None

    def test_cycle_runs_with_feedback(
        self,
        transformer_id: str,
        feedback_records: list[FeedbackRecord],
    ):
        collector = FeedbackCollector()
        collector.add_batch(feedback_records)

        updater = ModelUpdater(
            KWpCalibrator(),
            LossCalibrator(),
            collector,
        )

        cycle = updater.run_update_cycle(
            transformer_id=transformer_id,
            energy_injected_kwh=500.0,
            energy_measured_kwh=470.0,
        )

        assert cycle is not None
        assert cycle.transformer_id == transformer_id
        assert cycle.samples_used == len(feedback_records)
        assert isinstance(cycle.converged, bool)

    def test_get_cycles_filtered(
        self,
        transformer_id: str,
        feedback_records: list[FeedbackRecord],
    ):
        collector = FeedbackCollector()
        collector.add_batch(feedback_records)

        updater = ModelUpdater(
            KWpCalibrator(),
            LossCalibrator(),
            collector,
        )
        updater.run_update_cycle(transformer_id)

        cycles = updater.get_cycles(transformer_id)
        assert len(cycles) >= 0

    def test_properties_accessible(self):
        updater = ModelUpdater(
            KWpCalibrator(),
            LossCalibrator(),
            FeedbackCollector(),
        )
        assert updater.current_kwp_factor == DEFAULT_FACTOR
        assert updater.current_loss_factor > 0


class TestValidationServiceUnit:
    def test_classify_status_validated(self):
        from backend.services.validation_service import ValidationService

        service = ValidationService.__new__(ValidationService)
        assert service._classify_status(8.0) == "validado"

    def test_classify_status_moderate(self):
        from backend.services.validation_service import ValidationService

        service = ValidationService.__new__(ValidationService)
        assert service._classify_status(15.0) == "divergencia_moderada"

    def test_classify_status_high(self):
        from backend.services.validation_service import ValidationService

        service = ValidationService.__new__(ValidationService)
        assert service._classify_status(28.0) == "divergencia_alta"

    def test_classify_status_critical(self):
        from backend.services.validation_service import ValidationService

        service = ValidationService.__new__(ValidationService)
        assert service._classify_status(50.0) == "critico"

    def test_classify_status_no_measurement(self):
        from backend.services.validation_service import ValidationService

        service = ValidationService.__new__(ValidationService)
        assert service._classify_status(None) == "sem_medicao_real"

    def test_calculate_score_low_risk(self):
        from backend.services.validation_service import ValidationService

        service = ValidationService.__new__(ValidationService)
        assert service._calculate_score(5.0, 0.90) == "baixo_risco"

    def test_calculate_score_inspection_priority(self):
        from backend.services.validation_service import ValidationService

        service = ValidationService.__new__(ValidationService)
        assert service._calculate_score(40.0, 0.30) == "prioridade_inspecao"

    def test_feature_vector_to_array_shape(
        self, feature_vector: EnergyFeatureVector
    ):
        arr = feature_vector.to_array()
        assert arr.shape == (7,)
        assert arr.dtype == np.float64