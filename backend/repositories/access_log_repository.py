from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.access_log import AccessLog
from backend.repositories.base import BaseRepository


class AccessLogRepository(BaseRepository[AccessLog]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(AccessLog, session)

    async def create_log(
        self,
        action: str,
        user_id: int | None = None,
        matricula: str | None = None,
        resource: str | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
        success: bool = True,
    ) -> AccessLog:
        log = AccessLog(
            user_id=user_id,
            matricula=matricula,
            action=action,
            resource=resource,
            ip_address=ip_address,
            user_agent=user_agent,
            success=success,
        )
        return await self.save(log)

    async def list_by_user(
        self, user_id: int, offset: int = 0, limit: int = 50
    ) -> list[AccessLog]:
        stmt = (
            select(AccessLog)
            .where(AccessLog.user_id == user_id)
            .order_by(AccessLog.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def list_failures(
        self, since: datetime, offset: int = 0, limit: int = 50
    ) -> list[AccessLog]:
        stmt = (
            select(AccessLog)
            .where(
                AccessLog.success.is_(False),
                AccessLog.created_at >= since,
            )
            .order_by(AccessLog.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
