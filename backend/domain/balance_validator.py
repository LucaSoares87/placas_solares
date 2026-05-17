"""
Validações físicas de consistência do balanço energético.
Detecta inconsistências antes de persistir o resultado.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from backend.domain.energy_balance import BalanceInput


@dataclass
class ValidationIssue:
    code: str
    message: str
    severity: str  # warning | error


@dataclass
class ValidationReport:
    is_valid: bool
    issues: list[ValidationIssue]

    @property
    def errors(self) -> list[ValidationIssue]:
        return [i for i in self.issues if i.severity == "error"]

    @property
    def warnings(self) -> list[ValidationIssue]:
        return [i for i in self.issues if i.severity == "warning"]


def validate_balance_input(data: BalanceInput) -> ValidationReport:
    """
    Aplica validações físicas sobre os dados de entrada do balanço.
    Retorna relatório com erros e avisos.
    """
    issues: list[ValidationIssue] = []

    if data.measured_kwh < 0:
        issues.append(ValidationIssue(
            code="NEGATIVE_MEASURED",
            message="Energia medida não pode ser negativa.",
            severity="error",
        ))

    if len(data.uc_consumptions) == 0:
        issues.append(ValidationIssue(
            code="NO_UCS",
            message="Nenhuma UC associada ao transformador.",
            severity="warning",
        ))

    if any(c < 0 for c in data.uc_consumptions):
        issues.append(ValidationIssue(
            code="NEGATIVE_CONSUMPTION",
            message="Consumo estimado de UC com valor negativo detectado.",
            severity="warning",
        ))

    if any(g < 0 for g in data.uc_generations):
        issues.append(ValidationIssue(
            code="NEGATIVE_GENERATION",
            message="Geração estimada de UC com valor negativo detectado.",
            severity="warning",
        ))

    total_estimated = sum(data.uc_consumptions)
    if data.measured_kwh > 0 and total_estimated > data.measured_kwh * 3.0:
        issues.append(ValidationIssue(
            code="IMPLAUSIBLE_CONSUMPTION",
            message=(
                f"Consumo total estimado ({total_estimated:.2f} kWh) é mais de 3x "
                f"a energia medida ({data.measured_kwh:.2f} kWh). Verificar dados."
            ),
            severity="warning",
        ))

    if data.telemetered_kwh is not None and data.telemetered_kwh < 0:
        issues.append(ValidationIssue(
            code="NEGATIVE_TELEMETERED",
            message="Soma telemedida não pode ser negativa.",
            severity="error",
        ))

    return ValidationReport(
        is_valid=not any(i.severity == "error" for i in issues),
        issues=issues,
    )
