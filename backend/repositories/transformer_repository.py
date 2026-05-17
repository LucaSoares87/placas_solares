from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.transformer import Transformer
from backend.repositories.base import BaseRepository


class TransformerRepository(BaseRepository[Transformer]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(Transformer, session)

    async def get_by_transformer_id(self, transformer_id: str) -> Transformer | None:
        stmt = select(Transformer).where(Transformer.transformer_id == transformer_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_by_substation(
        self, substation: str, offset: int = 0, limit: int = 50
    ) -> list[Transformer]:
        stmt = (
            select(Transformer)
            .where(Transformer.substation == substation)
            .order_by(Transformer.transformer_id)
            .offset(offset)
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def list_by_feeder(
        self, feeder: str, offset: int = 0, limit: int = 50
    ) -> list[Transformer]:
        stmt = (
            select(Transformer)
            .where(Transformer.feeder == feeder)
            .order_by(Transformer.transformer_id)
            .offset(offset)
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def exists_by_transformer_id(self, transformer_id: str) -> bool:
        stmt = select(func.count()).select_from(Transformer).where(
            Transformer.transformer_id == transformer_id
        )
        result = await self.session.execute(stmt)
        return result.scalar_one() > 0

    async def update_uc_counts(
        self, transformer_id: str, uc_count: int, gd_count: int
    ) -> None:
        transformer = await self.get_by_transformer_id(transformer_id)
        if transformer:
            transformer.uc_count = uc_count
            transformer.gd_count = gd_count
            await self.session.flush()
