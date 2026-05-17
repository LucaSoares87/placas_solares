"""
Validação e controle de qualidade para leituras telemetradas.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from backend.core.config import settings


class TelemetryValidationError(ValueError):
    pass


class TelemetryValidator:
    # Limites físicos aceitáveis
    VOLTAGE_MIN_V = 80.0
    VOLTAGE_MAX_V = 600.0
    CURRENT_MIN_A = 0.0
    CURRENT_MAX_A = 1_500.0
    POWER_FACTOR_MIN = -1.0
    POWER_FACTOR_MAX = 1.0
    ACTIVE_POWER_MIN_KW = -500.0
    ACTIVE_POWER_MAX_KW = 10_000.0
    ENERGY_IMPORT_MAX_KWH = 1_000_000.0

    def validate(
        self, raw: dict[str, Any], source_type: str = "uc"
    ) -> dict[str, Any]:
        """
        Valida e normaliza um payload bruto.
        Lança TelemetryValidationError se campos obrigatórios estiverem ausentes.
        """
        source_id = raw.get("source_id") or raw.get("uc_code") or raw.get("transformer_id")
        if not source_id:
            raise TelemetryValidationError("source_id obrigatório.")

        measured_at = raw.get("measured_at")
        if not measured_at:
            raise TelemetryValidationError("measured_at obrigatório.")

        if isinstance(measured_at, str):
            measured_at = datetime.fromisoformat(measured_at)
        if measured_at.tzinfo is None:
            measured_at = measured_at.replace(tzinfo=timezone.utc)

        # Verifica se a leitura não é do futuro distante
        now = datetime.now(timezone.utc)
        tolerance = settings.TELEMETRY_TOLERANCE_MINUTES * 60
        if (measured_at - now).total_seconds() > tolerance:
            raise TelemetryValidationError(
                f"measured_at no futuro além da tolerância: {measured_at.isoformat()}"
            )

        return {
            "source_id": str(source_id),
            "measured_at": measured_at,
            "active_power_kw": self._safe_float(raw.get("active_power_kw")),
            "reactive_power_kvar": self._safe_float(raw.get("reactive_power_kvar")),
            "voltage_v": self._safe_float(raw.get("voltage_v")),
            "current_a": self._safe_float(raw.get("current_a")),
            "power_factor": self._safe_float(raw.get("power_factor")),
            "energy_kwh_import": self._safe_float(raw.get("energy_kwh_import")),
            "energy_kwh_export": self._safe_float(raw.get("energy_kwh_export")),
        }

    def quality_flag(self, validated: dict[str, Any]) -> str:
        """
        Retorna 'ok', 'suspect' ou 'invalid' conforme regras físicas.
        """
        issues: list[str] = []

        v = validated.get("voltage_v")
        if v is not None:
            if not (self.VOLTAGE_MIN_V <= v <= self.VOLTAGE_MAX_V):
                issues.append(f"voltage_v fora do range: {v}")

        pf = validated.get("power_factor")
        if pf is not None:
            if not (self.POWER_FACTOR_MIN <= pf <= self.POWER_FACTOR_MAX):
                issues.append(f"power_factor inválido: {pf}")

        kw = validated.get("active_power_kw")
        if kw is not None:
            if not (self.ACTIVE_POWER_MIN_KW <= kw <= self.ACTIVE_POWER_MAX_KW):
                issues.append(f"active_power_kw fora do range: {kw}")

        e_imp = validated.get("energy_kwh_import")
        if e_imp is not None and e_imp > self.ENERGY_IMPORT_MAX_KWH:
            issues.append(f"energy_kwh_import implausível: {e_imp}")

        if not issues:
            return "ok"

        # Tensão completamente fora de range é inválido; demais são suspeitos
        critical = any("voltage_v" in i and abs(
            float(i.split(": ")[-1]) - 230
        ) > 200 for i in issues)

        return "invalid" if critical else "suspect"

    @staticmethod
    def _safe_float(value: Any) -> float | None:
        if value is None:
            return None
        try:
            return float(value)
        except (TypeError, ValueError):
            return None
