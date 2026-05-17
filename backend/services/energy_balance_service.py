"""
Service de Balanço Energético.

Orquestra:
  1. Coleta das inferências do período
  2. Validação física dos dados
  3. Cálculo do balanço (domain puro)
  4. Persistência do resultado
  5. Retorno do response formatado
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from backend.domain.balance_validator import validate_balance_input
from backend.domain.energy_balance import (
    BalanceInput,
    BalanceThresholds,
    compute_balance,
    classify_operational_score,
)
from backend.repositories.energy_balance_repository import EnergyBalanceRepository
from backend.schemas.energy_balance import (
    BalanceComputeResponse,
    BalanceSummaryResponse,
    BatchBalanceResponse,
    ValidationIssueResponse,
)

logger = structlog.get_logger(__name__)


class EnergyBalanceService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repo = EnergyBalanceRepository(session)

    # ─────────────────────────────────────────────────────────────────────────
    # Cálculo individual
    # ─────────────────────────────────────────────────────────────────────────

    async def compute_transformer_balance(
        self,
        transformer_id: str,
        period_start: datetime,
        period_end: datetime,
        force_recalculate: bool = False,
    ) -> BalanceComputeResponse:
        log = logger.bind(
            transformer_id=transformer_id,
            period_start=period_start.isoformat(),
            period_end=period_end.isoformat(),
        )

        # Verificar se transformador existe
        transformer = await self._repo.get_transformer(transformer_id)
        if not transformer:
            raise ValueError(f"Transformador '{transformer_id}' não encontrado.")

        # Verificar se balanço já foi calculado para o período
        existing = await self._repo.find_existing_balance(
            transformer_id, period_start, period_end
        )
        if existing and not force_recalculate:
            log.info("balance.cache_hit")
            return self._to_response(existing, period_start, period_end, [])

        # Coletar inferências do período
        inferences = await self._repo.get_inferences_for_period(
            transformer_id, period_start, period_end
        )

        # Contagens de UCs
        uc_counts = await self._repo.get_uc_counts(transformer_id)

        # Montar input de domínio
        consumptions = [inf.consumption_estimated_kw or 0.0 for inf in inferences]
        generations = [inf.generation_kw or 0.0 for inf in inferences]
        injections = [
            ((inf.injection_kw_min or 0.0) + (inf.injection_kw_max or 0.0)) / 2.0
            for inf in inferences
        ]

        measured_kwh = float(transformer.rated_kva or 0.0) * 0.8

        balance_input = BalanceInput(
            transformer_id=transformer_id,
            measured_kwh=measured_kwh,
            uc_consumptions=consumptions,
            uc_generations=generations,
            uc_injections=injections,
            thresholds=BalanceThresholds(),
        )

        # Validação física
        validation_report = validate_balance_input(balance_input)
        if not validation_report.is_valid:
            log.warning(
                "balance.validation_failed",
                errors=[i.code for i in validation_report.errors],
            )

        # Cálculo do balanço (domínio puro)
        result = compute_balance(balance_input)

        # Enriquecer com dados reais de anomalias para score final
        from backend.models.energy_anomaly import EnergyAnomaly
        from sqlalchemy import select, func
        open_anomalies = await self._session.scalar(
            select(func.count(EnergyAnomaly.id)).where(
                EnergyAnomaly.transformer_id == transformer_id,
                EnergyAnomaly.resolved_at.is_(None),
            )
        ) or 0

        final_score = classify_operational_score(
            result.balance_status,
            open_anomalies=open_anomalies,
        )
        result.operational_score = final_score

        # Confiança média das inferências
        confidences = [inf.confidence or 0.0 for inf in inferences if inf.confidence]
        avg_confidence = round(
            sum(confidences) / len(confidences) if confidences else 0.0, 4
        )

        # Persistir
        saved = await self._repo.save_balance(
            transformer_id=transformer_id,
            period_start=period_start,
            period_end=period_end,
            measured_kwh=result.measured_kwh,
            estimated_consumption_kwh=result.estimated_consumption_kwh,
            estimated_generation_kwh=result.estimated_generation_kwh,
            estimated_injection_kwh=result.estimated_injection_kwh,
            technical_losses_kwh=result.technical_losses_kwh,
            residual_kwh=result.residual_kwh,
            absolute_error_kwh=result.absolute_error_kwh,
            percentage_error=result.percentage_error,
            balance_status=result.balance_status.value,
            operational_score=result.operational_score.value,
            uc_count=uc_counts["total"],
            telemetered_count=uc_counts["telemetered"],
            gd_count=uc_counts["with_gd"],
            confidence=avg_confidence,
            existing=existing,
        )
        await self._session.commit()

        log.info(
            "balance.computed",
            status=result.balance_status.value,
            pct_error=result.percentage_error,
            uc_count=uc_counts["total"],
        )

        issues = [
            ValidationIssueResponse(
                code=i.code,
                message=i.message,
                severity=i.severity,
            )
            for i in validation_report.issues
        ]

        return self._to_response(saved, period_start, period_end, issues)

    # ─────────────────────────────────────────────────────────────────────────
    # Cálculo em lote
    # ─────────────────────────────────────────────────────────────────────────

    async def compute_batch_balance(
        self,
        transformer_ids: list[str],
        period_start: datetime,
        period_end: datetime,
        force_recalculate: bool = False,
    ) -> BatchBalanceResponse:
        results: list[BalanceComputeResponse] = []
        failed: list[str] = []
        skipped = 0

        for transformer_id in transformer_ids:
            try:
                result = await self.compute_transformer_balance(
                    transformer_id=transformer_id,
                    period_start=period_start,
                    period_end=period_end,
                    force_recalculate=force_recalculate,
                )
                results.append(result)
            except ValueError:
                failed.append(transformer_id)
                logger.warning(
                    "balance.batch.transformer_not_found",
                    transformer_id=transformer_id,
                )
            except Exception as exc:
                failed.append(transformer_id)
                logger.error(
                    "balance.batch.compute_failed",
                    transformer_id=transformer_id,
                    error=str(exc),
                )

        return BatchBalanceResponse(
            total_requested=len(transformer_ids),
            total_computed=len(results),
            total_skipped=skipped,
            total_failed=len(failed),
            results=results,
            failed_transformer_ids=failed,
            computed_at=datetime.now(timezone.utc),
        )

    async def compute_all_transformers(
        self,
        period_start: datetime,
        period_end: datetime,
        force_recalculate: bool = False,
    ) -> BatchBalanceResponse:
        transformer_ids = await self._repo.get_transformer_ids_all()
        return await self.compute_batch_balance(
            transformer_ids, period_start, period_end, force_recalculate
        )

    # ─────────────────────────────────────────────────────────────────────────
    # Sumário analítico
    # ─────────────────────────────────────────────────────────────────────────

    async def get_balance_summary(
        self,
        period_start: datetime,
        period_end: datetime,
    ) -> BalanceSummaryResponse:
        data = await self._repo.get_balance_summary(period_start, period_end)
        return BalanceSummaryResponse(
            period_start=period_start,
            period_end=period_end,
            **data,
        )

    # ─────────────────────────────────────────────────────────────────────────
    # Helpers internos
    # ─────────────────────────────────────────────────────────────────────────

    @staticmethod
    def _to_response(
        balance,
        period_start: datetime,
        period_end: datetime,
        issues: list[ValidationIssueResponse],
    ) -> BalanceComputeResponse:
        return BalanceComputeResponse(
            transformer_id=balance.transformer_id,
            period_start=period_start,
            period_end=period_end,
            measured_kwh=balance.measured_kwh,
            estimated_consumption_kwh=balance.estimated_consumption_kwh,
            estimated_generation_kwh=balance.estimated_generation_kwh,
            estimated_injection_kwh=balance.estimated_injection_kwh,
            technical_losses_kwh=balance.technical_losses_kwh,
            residual_kwh=balance.residual_kwh,
            absolute_error_kwh=balance.absolute_error,
            percentage_error=balance.percentage_error,
            balance_status=balance.balance_status,
            operational_score=balance.operational_score,
            uc_count=balance.uc_count,
            telemetered_count=balance.telemetered_count,
            gd_count=balance.gd_count,
            confidence=getattr(balance, "confidence", 0.0) or 0.0,
            insufficient_data=balance.balance_status == "insufficient_data",
            validation_issues=issues,
            computed_at=balance.computed_at,
        )
