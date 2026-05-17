"""
Motor de detecção de anomalias energéticas.
Analisa balanços e inferências e persiste EnergyAnomaly quando detecta desvios.
"""

from __future__ import annotations

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from backend.domain.constants import (
    BALANCE_TOLERANCE_PCT,
    TRANSFORMER_OVERLOAD_THRESHOLD,
)
from backend.domain.entities import AnomalyType, RiskScore
from backend.models.energy_anomaly import EnergyAnomaly
from backend.models.transformer_balance import TransformerBalance
from backend.repositories.energy_anomaly_repository import EnergyAnomalyRepository
from backend.repositories.energy_inference_repository import EnergyInferenceRepository
from backend.repositories.transformer_repository import TransformerRepository

logger = structlog.get_logger(__name__)


class AnomalyDetector:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._anomaly_repo = EnergyAnomalyRepository(session)
        self._inf_repo = EnergyInferenceRepository(session)
        self._tr_repo = TransformerRepository(session)

    async def analyze_balance(self, balance: TransformerBalance) -> int:
        """
        Analisa um balanço energético e persiste as anomalias detectadas.

        Returns:
            Número de anomalias geradas.
        """
        anomalies: list[EnergyAnomaly] = []

        # ── Regra 1: Erro de balanço acima do limiar ──────────────────────────
        if abs(balance.percentage_error) > BALANCE_TOLERANCE_PCT * 100:
            severity = self._error_severity(balance.percentage_error)
            anomalies.append(EnergyAnomaly(
                transformer_id=balance.transformer_id,
                anomaly_type=AnomalyType.EXCESS_INJECTION.value
                if balance.percentage_error > 0
                else AnomalyType.NEGATIVE_CONSUMPTION.value,
                description=(
                    f"Erro de balanço de {balance.percentage_error:.2f}% "
                    f"no transformador {balance.transformer_id} "
                    f"no período {balance.period_start.date()} → {balance.period_end.date()}."
                ),
                severity=severity.value,
            ))

        # ── Regra 2: Geração maior que consumo estimado ──────────────────────
        if balance.estimated_generation_kwh > balance.estimated_consumption_kwh:
            anomalies.append(EnergyAnomaly(
                transformer_id=balance.transformer_id,
                anomaly_type=AnomalyType.IMPLAUSIBLE_GENERATION.value,
                description=(
                    f"Geração estimada ({balance.estimated_generation_kwh:.2f} kWh) "
                    f"supera consumo ({balance.estimated_consumption_kwh:.2f} kWh) "
                    f"no transformador {balance.transformer_id}."
                ),
                severity=RiskScore.HIGH.value,
            ))

        # ── Regra 3: Sobrecarga do transformador ─────────────────────────────
        transformer = await self._tr_repo.get_by_transformer_id(
            balance.transformer_id
        )
        if transformer:
            load_ratio = balance.measured_kwh / max(transformer.rated_kva, 1)
            if load_ratio > TRANSFORMER_OVERLOAD_THRESHOLD:
                severity = (
                    RiskScore.CRITICAL if load_ratio > 1.10 else RiskScore.HIGH
                )
                anomalies.append(EnergyAnomaly(
                    transformer_id=balance.transformer_id,
                    anomaly_type=AnomalyType.SUDDEN_SPIKE.value,
                    description=(
                        f"Transformador {balance.transformer_id} com carga "
                        f"{load_ratio * 100:.1f}% da nominal "
                        f"({transformer.rated_kva} kVA)."
                    ),
                    severity=severity.value,
                ))

        # ── Regra 4: Taxa de GD implausível ──────────────────────────────────
        if balance.gd_penetration_rate > 0.80:
            anomalies.append(EnergyAnomaly(
                transformer_id=balance.transformer_id,
                anomaly_type=AnomalyType.IMPLAUSIBLE_GENERATION.value,
                description=(
                    f"Taxa de penetração de GD de "
                    f"{balance.gd_penetration_rate * 100:.1f}% é atipicamente alta "
                    f"no transformador {balance.transformer_id}."
                ),
                severity=RiskScore.MEDIUM.value,
            ))

        # ── Persiste anomalias detectadas ────────────────────────────────────
        for anomaly in anomalies:
            self._session.add(anomaly)

        if anomalies:
            await self._session.flush()
            logger.info(
                "anomaly_detector.anomalies_persisted",
                transformer_id=balance.transformer_id,
                count=len(anomalies),
            )

        return len(anomalies)

    async def analyze_inference(self, inference_id: int) -> int:
        """Analisa uma inferência individual em busca de anomalias."""
        inference = await self._inf_repo.get_by_id(inference_id)
        if not inference:
            return 0

        anomalies: list[EnergyAnomaly] = []

        # Consumo negativo
        if inference.consumption_estimated_kw < 0:
            anomalies.append(EnergyAnomaly(
                uc_code=inference.uc_code,
                transformer_id=inference.transformer_id,
                anomaly_type=AnomalyType.NEGATIVE_CONSUMPTION.value,
                description=(
                    f"UC {inference.uc_code} apresenta consumo estimado negativo: "
                    f"{inference.consumption_estimated_kw:.4f} kW."
                ),
                severity=RiskScore.HIGH.value,
            ))

        # Injeção maior que geração
        if (
            inference.injection_kw_max is not None
            and inference.generation_kw is not None
            and inference.injection_kw_max > inference.generation_kw * 1.1
        ):
            anomalies.append(EnergyAnomaly(
                uc_code=inference.uc_code,
                transformer_id=inference.transformer_id,
                anomaly_type=AnomalyType.EXCESS_INJECTION.value,
                description=(
                    f"UC {inference.uc_code}: injeção máxima "
                    f"({inference.injection_kw_max:.4f} kW) > "
                    f"geração ({inference.generation_kw:.4f} kW)."
                ),
                severity=RiskScore.MEDIUM.value,
            ))

        for anomaly in anomalies:
            self._session.add(anomaly)

        if anomalies:
            await self._session.flush()

        return len(anomalies)

    @staticmethod
    def _error_severity(percentage_error: float) -> RiskScore:
        abs_err = abs(percentage_error)
        if abs_err > 25:
            return RiskScore.CRITICAL
        if abs_err > 15:
            return RiskScore.HIGH
        if abs_err > 5:
            return RiskScore.MEDIUM
        return RiskScore.LOW
