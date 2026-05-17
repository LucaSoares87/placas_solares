"""
Helpers para extrair sessão de banco e outros recursos do contexto ARQ.
"""

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession


@asynccontextmanager
async def db_session(ctx: dict) -> AsyncGenerator[AsyncSession, None]:
    """
    Cria uma sessão de banco a partir da factory injetada no contexto do worker.

    Uso:
        async with db_session(ctx) as session:
            ...
    """
    factory = ctx.get("db_factory")
    if factory is None:
        raise RuntimeError("db_factory não encontrada no contexto do worker.")

    async with factory() as session:
        async with session.begin():
            yield session
