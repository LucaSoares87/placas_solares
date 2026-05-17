"""
Repositório para persistência e consulta de balanços energéticos.
Reutiliza TransformerBalance model já definido nos atos anteriores.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

import structlog
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.consumer_unit import ConsumerUnit
from backend.models.energy_inference import EnergyInference
from backend.models.transformer import Transformer
from backend.models.transformer_balance import TransformerBalance

logger = structlog.get_logger(__name__)


class EnergyBalanceRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    # ─────────────────────────────────────────────────────────────────────────
    # Leitura de dados para cálculo
    # ─────────────────────────────────────────────────────────────────────────

    async def get_transformer(self, transformer_id: str) -> Optional[Transformer]:
        return await self._session.scalar(
            select(Transformer).where(
                Transformer.transformer_id == transformer_id
            )
        )

    async def get_transformer_ids_all(self) -> list[str]:
        result = await self._session.execute(
            select(Transformer.transformer_id).order_by(Transformer.transformer_id)
        )
        return list(result.scalars().all())

    async def get_inferences_for_period(
        self,
        transformer_id: str,
        period_start: datetime,
        period_end: datetime,
    ) -> list[EnergyInference]:
        """
        Retorna a última inferência de cada UC do transformador
        dentro do período informado.
        """
        latest_subq = (
            select(
                EnergyInference.uc_code,
                func.max(EnergyInference.computed_at).label("max_ts"),
            )
            .where(
                EnergyInference.transformer_id == transformer_id,
                EnergyInference.computed_at >= period_start,
                EnergyInference.computed_at <= period_end,
            )
            .group_by(EnergyInference.uc_code)
            .subquery("li_sub")
        )

        stmt = (
            select(EnergyInference)
            .join(
                latest_subq,
                and_(
                    EnergyInference.uc_code == latest_subq.c.uc_code,
                    EnergyInference.computed_at == latest_subq.c.max_ts,
                ),
            )
            .where(EnergyInference.transformer_id == transformer_id)
        )

        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def get_uc_counts(self, transformer_id: str) -> dict:
        from sqlalchemy import case
        result = await self._session.execute(
            select(
                func.count(ConsumerUnit.id).label("total"),
                func.sum(
                    case((ConsumerUnit.is_telemetered.is_(True), 1), else_=0)
                ).label("telemetered"),
                func.sum(
                    case((ConsumerUnit.has_gd.is_(True), 1), else_=0)
                ).label("with_gd"),
            ).where(ConsumerUnit.transformer_id == transformer_id)
        )
        row = result.one()
        return {
            "total": int(row.total or 0),
            "telemetered": int(row.telemetered or 0),
            "with_gd": int(row.with_gd or 0),
        }

    # ─────────────────────────────────────────────────────────────────────────
    # Verificação de existência
    # ─────────────────────────────────────────────────────────────────────────

    async def find_existing_balance(
        self,
        transformer_id: str,
        period_start: datetime,
        period_end: datetime,
    ) -> Optional[TransformerBalance]:
        return await self._session.scalar(
            select(TransformerBalance).where(
                TransformerBalance.transformer_id == transformer_id,
                TransformerBalance.period_start == period_start,
                TransformerBalance.period_end == period_end,
            )
        )

    # ─────────────────────────────────────────────────────────────────────────
    # Persistência
    # ─────────────────────────────────────────────────────────────────────────

    async def save_balance(
        self,
        transformer_id: str,
        period_start: datetime,
        period_end: datetime,
        measured_kwh: float,
        estimated_consumption_kwh: float,
        estimated_generation_kwh: float,
        estimated_injection_kwh: float,
        technical_losses_kwh: float,
        residual_kwh: float,
        absolute_error_kwh: float,
        percentage_error: float,
        balance_status: str,
        operational_score: str,
        uc_count: int,
        telemetered_count: int,
        gd_count: int,
        confidence: float,
        existing: Optional[TransformerBalance] = None,
    ) -> TransformerBalance:
        now = datetime.now(timezone.utc)

        if existing:
            existing.measured_kwh = measured_kwh
            existing.estimated_consumption_kwh = estimated_consumption_kwh
            existing.estimated_generation_kwh = estimated_generation_kwh
            existing.estimated_injection_kwh = estimated_injection_kwh
            existing.technical_losses_kwh = technical_losses_kwh
            existing.residual_kwh = residual_kwh
            existing.absolute_error = absolute_error_kwh
            existing.percentage_error = percentage_error
            existing.balance_status = balance_status
            existing.operational_score = operational_score
            existing.uc_count = uc_count
            existing.telemetered_count = telemetered_count
            existing.gd_count = gd_count
            existing.computed_at = now
            await self._session.flush()
            return existing

        balance = TransformerBalance(
            transformer_id=transformer_id,
            period_start=period_start,
            period_end=period_end,
            measured_kwh=measured_kwh,
            estimated_consumption_kwh=estimated_consumption_kwh,
            estimated_generation_kwh=estimated_generation_kwh,
            estimated_injection_kwh=estimated_injection_kwh,
            technical_losses_kwh=technical_losses_kwh,
            residual_kwh=residual_kwh,
            absolute_error=absolute_error_kwh,
            percentage_error=percentage_error,
            balance_status=balance_status,
            operational_score=operational_score,
            uc_count=uc_count,
            telemetered_count=telemetered_count,
            gd_count=gd_count,
            computed_at=now,
        )
        self._session.add(balance)
        await self._session.flush()
        return balance

    # ─────────────────────────────────────────────────────────────────────────
    # Consultas analíticas
    # ─────────────────────────────────────────────────────────────────────────

    async def get_balance_summary(
        self,
        period_start: datetime,
        period_end: datetime,
    ) -> dict:
        from sqlalchemy import case as sa_case

        latest_subq = (
            select(
                TransformerBalance.transformer_id,
                func.max(TransformerBalance.computed_at).label("max_ts"),
            )
            .where(
                TransformerBalance.period_start >= period_start,
                TransformerBalance.period_end <= period_end,
            )
            .group_by(TransformerBalance.transformer_id)
            .subquery("ls")
        )

        stmt = (
            select(TransformerBalance)
            .join(
                latest_subq,
                and_(
                    TransformerBalance.transformer_id == latest_subq.c.transformer_id,
                    TransformerBalance.computed_at == latest_subq.c.max_ts,
                ),
            )
            .subquery("bal")
        )

        agg = await self._session.execute(
            select(
                func.count(stmt.c.transformer_id).label("transformer_count"),
                func.avg(stmt.c.percentage_error).label("avg_pct_error"),
                func.max(stmt.c.percentage_error).label("max_pct_error"),
                func.min(stmt.c.percentage_error).label("min_pct_error"),
                func.sum(stmt.c.measured_kwh).label("total_measured"),
                func.sum(stmt.c.estimated_consumption_kwh).label("total_consumption"),
                func.sum(stmt.c.estimated_generation_kwh).label("total_generation"),
                func.sum(stmt.c.technical_losses_kwh).label("total_losses"),
                func.sum(stmt.c.residual_kwh).label("total_residual"),
                func.sum(
                    sa_case((stmt.c.balance_status == "balanced", 1), else_=0)
                ).label("balanced"),
                func.sum(
                    sa_case((stmt.c.balance_status == "acceptable", 1), else_=0)
                ).label("acceptable"),
                func.sum(
                    sa_case((stmt.c.balance_status == "high_loss", 1), else_=0)
                ).label("high_loss"),
                func.sum(
                    sa_case((stmt.c.balance_status == "critical", 1), else_=0)
                ).label("critical"),
                func.sum(
                    sa_case((stmt.c.balance_status == "insufficient_data", 1), else_=0)
                ).label("insufficient_data"),
            )
        )
        row = agg.one()

        return {
            "transformer_count": int(row.transformer_count or 0),
            "avg_percentage_error": round(float(row.avg_pct_error or 0.0), 4),
            "max_percentage_error": round(float(row.max_pct_error or 0.0), 4),
            "min_percentage_error": round(float(row.min_pct_error or 0.0), 4),
            "total_measured_kwh": round(float(row.total_measured or 0.0), 4),
            "total_estimated_consumption_kwh": round(float(row.total_consumption or 0.0), 4),
            "total_estimated_generation_kwh": round(float(row.total_generation or 0.0), 4),
            "total_technical_losses_kwh": round(float(row.total_losses or 0.0), 4),
            "total_residual_kwh": round(float(row.total_residual or 0.0), 4),
            "balanced_count": int(row.balanced or 0),
            "acceptable_count": int(row.acceptable or 0),
            "high_loss_count": int(row.high_loss or 0),
            "critical_count": int(row.critical or 0),
            "insufficient_data_count": int(row.insufficient_data or 0),
        }
