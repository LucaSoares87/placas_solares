from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.user import AuthorizedUser
from backend.repositories.base import BaseRepository


class UserRepository(BaseRepository[AuthorizedUser]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(AuthorizedUser, session)

    async def get_by_matricula(self, matricula: str) -> AuthorizedUser | None:
        stmt = select(AuthorizedUser).where(AuthorizedUser.matricula == matricula)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_email(self, email: str) -> AuthorizedUser | None:
        stmt = select(AuthorizedUser).where(AuthorizedUser.email == email)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_active_by_matricula(self, matricula: str) -> AuthorizedUser | None:
        stmt = select(AuthorizedUser).where(
            AuthorizedUser.matricula == matricula,
            AuthorizedUser.ativo.is_(True),
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_active(self, offset: int = 0, limit: int = 20) -> list[AuthorizedUser]:
        stmt = (
            select(AuthorizedUser)
            .where(AuthorizedUser.ativo.is_(True))
            .order_by(AuthorizedUser.nome)
            .offset(offset)
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
