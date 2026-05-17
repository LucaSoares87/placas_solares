"""
Regras de domínio puras para cálculo de balanço energético.
Sem dependência de banco, HTTP ou framework.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


# ─────────────────────────────────────────────────────────────────────────────
# Enums
# ─────────────────────────────────────────────────────────────────────────────

class BalanceStatus(str, Enum):
    BALANCED = "balanced"
    ACCEPTABLE = "acceptable"
    HIGH_LOSS = "high_loss"
    CRITICAL = "critical"
    INSUFFICIENT_DATA = "insufficient_data"


class OperationalScore(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


# ─────────────────────────────────────────────────────────────────────────────
# Thresholds configuráveis
# ─────────────────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class BalanceThresholds:
    """Limites operacionais para classificação do balanço."""

    balanced_pct: float = 5.0        # <= 5% → balanced
    acceptable_pct: float = 10.0     # <= 10% → acceptable
    high_loss_pct: float = 20.0      # <= 20% → high_loss
    # > 20% → critical

    technical_loss_rate: float = 0.03  # 3% da energia medida como perdas técnicas
    min_ucs_for_balance: int = 1
    min_measured_kwh: float = 0.01


DEFAULT_THRESHOLDS = BalanceThresholds()


# ─────────────────────────────────────────────────────────────────────────────
# Input / Output de domínio
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class BalanceInput:
    """Dados de entrada para o cálculo de balanço de um transformador."""

    transformer_id: str
    measured_kwh: float                          # energia medida no transformador
    uc_consumptions: list[float]                 # consumo estimado por UC (kWh)
    uc_generations: list[float]                  # geração estimada por UC (kWh)
    uc_injections: list[float]                   # injeção estimada por UC (kWh)
    telemetered_kwh: Optional[float] = None      # soma das UCs telemedidas (ground truth parcial)
    thresholds: BalanceThresholds = field(
        default_factory=lambda: DEFAULT_THRESHOLDS
    )


@dataclass
class BalanceResult:
    """Resultado do cálculo de balanço energético."""

    transformer_id: str

    # Energias agregadas
    measured_kwh: float
    estimated_consumption_kwh: float
    estimated_generation_kwh: float
    estimated_injection_kwh: float
    technical_losses_kwh: float

    # Resíduo = medido - (consumo - geração + injeção) - perdas
    residual_kwh: float

    # Métricas de erro
    absolute_error_kwh: float
    percentage_error: float

    # Classificações
    balance_status: BalanceStatus
    operational_score: OperationalScore

    # Contagens
    uc_count: int
    telemetered_count: int = 0

    # Confiança agregada da estimativa
    confidence: float = 0.0

    # Flag de dados insuficientes
    insufficient_data: bool = False


# ─────────────────────────────────────────────────────────────────────────────
# Funções de domínio puras
# ─────────────────────────────────────────────────────────────────────────────

def classify_balance_status(
    percentage_error: float,
    thresholds: BalanceThresholds,
) -> BalanceStatus:
    abs_pct = abs(percentage_error)
    if abs_pct <= thresholds.balanced_pct:
        return BalanceStatus.BALANCED
    if abs_pct <= thresholds.acceptable_pct:
        return BalanceStatus.ACCEPTABLE
    if abs_pct <= thresholds.high_loss_pct:
        return BalanceStatus.HIGH_LOSS
    return BalanceStatus.CRITICAL


def classify_operational_score(
    balance_status: BalanceStatus,
    open_anomalies: int = 0,
    has_unregistered_gd: bool = False,
) -> OperationalScore:
    """
    Score operacional combinando status do balanço,
    anomalias abertas e GD não cadastrada.
    """
    if balance_status == BalanceStatus.CRITICAL or open_anomalies >= 3:
        return OperationalScore.CRITICAL
    if balance_status == BalanceStatus.HIGH_LOSS or open_anomalies >= 1 or has_unregistered_gd:
        return OperationalScore.HIGH
    if balance_status == BalanceStatus.ACCEPTABLE:
        return OperationalScore.MEDIUM
    return OperationalScore.LOW


def compute_technical_losses(
    measured_kwh: float,
    rate: float,
) -> float:
    """Perdas técnicas estimadas como percentual da energia medida."""
    return round(measured_kwh * rate, 4)


def compute_balance(input_data: BalanceInput) -> BalanceResult:
    """
    Calcula o balanço energético de um transformador.

    Fórmula principal:
        residual = medido - (consumo_total - geração_total + injeção_total) - perdas_técnicas

    O resíduo representa a diferença não explicada entre o que entrou na rede
    (medido pelo transformador) e o que foi estimado para as UCs.
    """
    t = input_data.thresholds

    if input_data.measured_kwh < t.min_measured_kwh:
        return BalanceResult(
            transformer_id=input_data.transformer_id,
            measured_kwh=input_data.measured_kwh,
            estimated_consumption_kwh=0.0,
            estimated_generation_kwh=0.0,
            estimated_injection_kwh=0.0,
            technical_losses_kwh=0.0,
            residual_kwh=0.0,
            absolute_error_kwh=0.0,
            percentage_error=0.0,
            balance_status=BalanceStatus.INSUFFICIENT_DATA,
            operational_score=OperationalScore.MEDIUM,
            uc_count=len(input_data.uc_consumptions),
            insufficient_data=True,
        )

    total_consumption = round(sum(input_data.uc_consumptions), 4)
    total_generation = round(sum(input_data.uc_generations), 4)
    total_injection = round(sum(input_data.uc_injections), 4)
    technical_losses = compute_technical_losses(input_data.measured_kwh, t.technical_loss_rate)

    # Energia líquida estimada que deveria sair do transformador:
    # consumo das UCs reduzido pela geração local, mais injeção de volta à rede,
    # mais perdas técnicas da linha
    estimated_net_load = total_consumption - total_generation + total_injection + technical_losses

    residual = round(input_data.measured_kwh - estimated_net_load, 4)
    absolute_error = round(abs(residual), 4)
    percentage_error = round(
        (absolute_error / input_data.measured_kwh) * 100.0
        if input_data.measured_kwh > 0
        else 0.0,
        4,
    )

    balance_status = classify_balance_status(percentage_error, t)
    operational_score = classify_operational_score(balance_status)

    return BalanceResult(
        transformer_id=input_data.transformer_id,
        measured_kwh=round(input_data.measured_kwh, 4),
        estimated_consumption_kwh=total_consumption,
        estimated_generation_kwh=total_generation,
        estimated_injection_kwh=total_injection,
        technical_losses_kwh=technical_losses,
        residual_kwh=residual,
        absolute_error_kwh=absolute_error,
        percentage_error=percentage_error,
        balance_status=balance_status,
        operational_score=operational_score,
        uc_count=len(input_data.uc_consumptions),
    )
