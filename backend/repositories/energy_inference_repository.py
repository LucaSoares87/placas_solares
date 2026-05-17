from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.energy_inference import EnergyInference
from backend.repositories.base import BaseRepository


class EnergyInferenceRepository(BaseRepository[EnergyInference]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(EnergyInference, session)

    async def get_latest_by_uc(self, uc_code: str) -> EnergyInference | None:
        stmt = (
            select(EnergyInference)
            .where(EnergyInference.uc_code == uc_code)
            .order_by(EnergyInference.computed_at.desc())
            .limit(1)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_by_transformer(
        self, transformer_id: str, offset: int = 0, limit: int = 100
    ) -> list[EnergyInference]:
        stmt = (
            select(EnergyInference)
            .where(EnergyInference.transformer_id == transformer_id)
            .order_by(EnergyInference.computed_at.desc())
            .offset(offset)
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def list_by_period(
        self, start: datetime, end: datetime, offset: int = 0, limit: int = 200
    ) -> list[EnergyInference]:
        stmt = (
            select(EnergyInference)
            .where(
                EnergyInference.computed_at >= start,
                EnergyInference.computed_at <= end,
            )
            .order_by(EnergyInference.computed_at.desc())
            .offset(offset)
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
