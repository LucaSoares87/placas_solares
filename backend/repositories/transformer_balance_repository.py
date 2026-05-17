from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.transformer_balance import TransformerBalance
from backend.repositories.base import BaseRepository


class TransformerBalanceRepository(BaseRepository[TransformerBalance]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(TransformerBalance, session)

    async def get_latest_by_transformer(
        self, transformer_id: str
    ) -> TransformerBalance | None:
        stmt = (
            select(TransformerBalance)
            .where(TransformerBalance.transformer_id == transformer_id)
            .order_by(TransformerBalance.computed_at.desc())
            .limit(1)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_by_transformer(
        self,
        transformer_id: str,
        offset: int = 0,
        limit: int = 30,
    ) -> list[TransformerBalance]:
        stmt = (
            select(TransformerBalance)
            .where(TransformerBalance.transformer_id == transformer_id)
            .order_by(TransformerBalance.period_start.desc())
            .offset(offset)
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def list_by_period(
        self,
        start: datetime,
        end: datetime,
        offset: int = 0,
        limit: int = 100,
    ) -> list[TransformerBalance]:
        stmt = (
            select(TransformerBalance)
            .where(
                TransformerBalance.period_start >= start,
                TransformerBalance.period_end <= end,
            )
            .order_by(TransformerBalance.computed_at.desc())
            .offset(offset)
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def list_critical(
        self, offset: int = 0, limit: int = 50
    ) -> list[TransformerBalance]:
        from backend.domain.entities import RiskScore
        stmt = (
            select(TransformerBalance)
            .where(TransformerBalance.operational_score == RiskScore.CRITICAL.value)
            .order_by(TransformerBalance.computed_at.desc())
            .offset(offset)
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
