from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.consumer_unit import ConsumerUnit
from backend.repositories.base import BaseRepository


class ConsumerUnitRepository(BaseRepository[ConsumerUnit]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(ConsumerUnit, session)

    async def get_by_uc_code(self, uc_code: str) -> ConsumerUnit | None:
        stmt = select(ConsumerUnit).where(ConsumerUnit.uc_code == uc_code)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_by_transformer(
        self, transformer_id: str, offset: int = 0, limit: int = 100
    ) -> list[ConsumerUnit]:
        stmt = (
            select(ConsumerUnit)
            .where(ConsumerUnit.transformer_id == transformer_id)
            .order_by(ConsumerUnit.uc_code)
            .offset(offset)
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def list_with_gd(self, offset: int = 0, limit: int = 100) -> list[ConsumerUnit]:
        stmt = (
            select(ConsumerUnit)
            .where(ConsumerUnit.has_gd.is_(True))
            .order_by(ConsumerUnit.uc_code)
            .offset(offset)
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def list_telemetered(self, offset: int = 0, limit: int = 100) -> list[ConsumerUnit]:
        stmt = (
            select(ConsumerUnit)
            .where(ConsumerUnit.is_telemetered.is_(True))
            .order_by(ConsumerUnit.uc_code)
            .offset(offset)
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def count_by_transformer(self, transformer_id: str) -> int:
        stmt = select(func.count()).select_from(ConsumerUnit).where(
            ConsumerUnit.transformer_id == transformer_id
        )
        result = await self.session.execute(stmt)
        return result.scalar_one()

    async def count_gd_by_transformer(self, transformer_id: str) -> int:
        stmt = select(func.count()).select_from(ConsumerUnit).where(
            ConsumerUnit.transformer_id == transformer_id,
            ConsumerUnit.has_gd.is_(True),
        )
        result = await self.session.execute(stmt)
        return result.scalar_one()

    async def exists_by_uc_code(self, uc_code: str) -> bool:
        stmt = select(func.count()).select_from(ConsumerUnit).where(
            ConsumerUnit.uc_code == uc_code
        )
        result = await self.session.execute(stmt)
        return result.scalar_one() > 0
