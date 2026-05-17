"""
Testes unitários das funções de domínio do balanço energético.
Zero dependências externas — apenas lógica pura.
"""

from __future__ import annotations

import pytest

from backend.domain.energy_balance import (
    BalanceInput,
    BalanceStatus,
    BalanceThresholds,
    OperationalScore,
    classify_balance_status,
    classify_operational_score,
    compute_balance,
    compute_technical_losses,
)
from backend.domain.balance_validator import validate_balance_input


DEFAULT_T = BalanceThresholds()


# ─────────────────────────────────────────────────────────────────────────────
# classify_balance_status
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.parametrize(
    "pct_error, expected_status",
    [
        (0.0, BalanceStatus.BALANCED),
        (4.99, BalanceStatus.BALANCED),
        (5.0, BalanceStatus.BALANCED),
        (5.01, BalanceStatus.ACCEPTABLE),
        (10.0, BalanceStatus.ACCEPTABLE),
        (10.01, BalanceStatus.HIGH_LOSS),
        (20.0, BalanceStatus.HIGH_LOSS),
        (20.01, BalanceStatus.CRITICAL),
        (50.0, BalanceStatus.CRITICAL),
    ],
)
def test_classify_balance_status(pct_error, expected_status):
    assert classify_balance_status(pct_error, DEFAULT_T) == expected_status


def test_classify_balance_status_negative_error():
    # Erro negativo (excesso de injeção) também é tratado em abs
    assert classify_balance_status(-4.0, DEFAULT_T) == BalanceStatus.BALANCED
    assert classify_balance_status(-25.0, DEFAULT_T) == BalanceStatus.CRITICAL


# ─────────────────────────────────────────────────────────────────────────────
# classify_operational_score
# ─────────────────────────────────────────────────────────────────────────────

def test_score_critical_from_status():
    score = classify_operational_score(BalanceStatus.CRITICAL)
    assert score == OperationalScore.CRITICAL


def test_score_critical_from_anomalies():
    score = classify_operational_score(BalanceStatus.BALANCED, open_anomalies=3)
    assert score == OperationalScore.CRITICAL


def test_score_high_from_high_loss():
    score = classify_operational_score(BalanceStatus.HIGH_LOSS)
    assert score == OperationalScore.HIGH


def test_score_high_from_unregistered_gd():
    score = classify_operational_score(
        BalanceStatus.BALANCED, has_unregistered_gd=True
    )
    assert score == OperationalScore.HIGH


def test_score_medium_from_acceptable():
    score = classify_operational_score(BalanceStatus.ACCEPTABLE)
    assert score == OperationalScore.MEDIUM


def test_score_low_from_balanced():
    score = classify_operational_score(BalanceStatus.BALANCED)
    assert score == OperationalScore.LOW


# ─────────────────────────────────────────────────────────────────────────────
# compute_technical_losses
# ─────────────────────────────────────────────────────────────────────────────

def test_technical_losses_basic():
    losses = compute_technical_losses(1000.0, 0.03)
    assert losses == pytest.approx(30.0)


def test_technical_losses_zero():
    assert compute_technical_losses(0.0, 0.03) == pytest.approx(0.0)


# ─────────────────────────────────────────────────────────────────────────────
# compute_balance — cenários reais
# ─────────────────────────────────────────────────────────────────────────────

def _make_input(
    measured: float,
    consumptions: list[float],
    generations: list[float] | None = None,
    injections: list[float] | None = None,
) -> BalanceInput:
    n = len(consumptions)
    return BalanceInput(
        transformer_id="TR-TEST",
        measured_kwh=measured,
        uc_consumptions=consumptions,
        uc_generations=generations or [0.0] * n,
        uc_injections=injections or [0.0] * n,
    )


def test_compute_balance_balanced():
    """
    Cenário: medido = 103 kWh, consumo = 100 kWh, perdas = 3 kWh
    → resíduo próximo de zero → balanced
    """
    inp = _make_input(measured=103.0, consumptions=[100.0])
    result = compute_balance(inp)
    assert result.balance_status == BalanceStatus.BALANCED
    assert abs(result.residual_kwh) <= 5.0


def test_compute_balance_with_generation():
    """
    UC com GD: consumo = 80 kWh, geração = 40 kWh, injeção = 10 kWh
    Medido no transformador = 53 kWh (80 - 40 + 10 + 3 perdas)
    """
    inp = _make_input(
        measured=53.0,
        consumptions=[80.0],
        generations=[40.0],
        injections=[10.0],
    )
    result = compute_balance(inp)
    assert result.estimated_generation_kwh == pytest.approx(40.0)
    assert result.estimated_injection_kwh == pytest.approx(10.0)
    assert result.balance_status in (
        BalanceStatus.BALANCED, BalanceStatus.ACCEPTABLE
    )


def test_compute_balance_critical():
    """
    Medido muito diferente do estimado → critical
    """
    inp = _make_input(measured=1000.0, consumptions=[100.0])
    result = compute_balance(inp)
    assert result.balance_status == BalanceStatus.CRITICAL
    assert result.percentage_error > 20.0


def test_compute_balance_insufficient_data():
    inp = _make_input(measured=0.0, consumptions=[])
    result = compute_balance(inp)
    assert result.balance_status == BalanceStatus.INSUFFICIENT_DATA
    assert result.insufficient_data is True


def test_compute_balance_multiple_ucs():
    consumptions = [50.0, 30.0, 20.0]
    generations = [10.0, 5.0, 0.0]
    injections = [5.0, 2.0, 0.0]
    measured = sum(consumptions) - sum(generations) + sum(injections) + 3.0
    inp = _make_input(
        measured=measured,
        consumptions=consumptions,
        generations=generations,
        injections=injections,
    )
    result = compute_balance(inp)
    assert result.uc_count == 3
    assert result.balance_status == BalanceStatus.BALANCED


# ─────────────────────────────────────────────────────────────────────────────
# validate_balance_input
# ─────────────────────────────────────────────────────────────────────────────

def test_validation_negative_measured():
    inp = _make_input(measured=-1.0, consumptions=[100.0])
    report = validate_balance_input(inp)
    assert not report.is_valid
    codes = [i.code for i in report.errors]
    assert "NEGATIVE_MEASURED" in codes


def test_validation_no_ucs():
    inp = _make_input(measured=100.0, consumptions=[])
    report = validate_balance_input(inp)
    assert report.is_valid
    codes = [i.code for i in report.warnings]
    assert "NO_UCS" in codes


def test_validation_implausible_consumption():
    inp = _make_input(measured=100.0, consumptions=[500.0])
    report = validate_balance_input(inp)
    assert report.is_valid
    codes = [i.code for i in report.warnings]
    assert "IMPLAUSIBLE_CONSUMPTION" in codes


def test_validation_clean_input():
    inp = _make_input(measured=100.0, consumptions=[80.0], generations=[10.0])
    report = validate_balance_input(inp)
    assert report.is_valid
    assert len(report.issues) == 0
