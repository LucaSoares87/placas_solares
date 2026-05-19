from __future__ import annotations

from types import SimpleNamespace

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from backend.app.main import application
from backend.core.database import Base, get_db_session

TEST_DATABASE_URL = (
    "postgresql+asyncpg://postgres:postgres@localhost:5432/energy_platform_test"
)

test_engine = create_async_engine(
    TEST_DATABASE_URL,
    echo=False,
    poolclass=NullPool,
)

TestSessionFactory = async_sessionmaker(
    bind=test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)


async def _override_get_db():
    async with TestSessionFactory() as session:
        try:
            yield session
        finally:
            await session.rollback()


async def _override_user_admin():
    return SimpleNamespace(
        id=1,
        matricula="MAT001",
        nome="Engenheiro Teste",
        email="eng@test.com",
        perfil="engenharia",
        ativo=True,
    )


async def _override_user_readonly():
    return SimpleNamespace(
        id=2,
        matricula="MAT002",
        nome="Consulta Teste",
        email="consulta@test.com",
        perfil="consulta",
        ativo=True,
    )


def _install_auth_override(user_dependency, user_override):
    application.dependency_overrides[user_dependency] = user_override


def _clear_overrides():
    application.dependency_overrides.clear()


@pytest_asyncio.fixture(scope="session", autouse=True)
async def setup_database():
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    yield

    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await test_engine.dispose()


@pytest_asyncio.fixture
async def db_session():
    async with TestSessionFactory() as session:
        try:
            yield session
        finally:
            await session.rollback()
            await session.close()


@pytest_asyncio.fixture
async def client(db_session: AsyncSession):
    async def override_get_db():
        yield db_session

    application.dependency_overrides[get_db_session] = override_get_db

    async with AsyncClient(
        transport=ASGITransport(app=application),
        base_url="http://test",
    ) as ac:
        yield ac

    _clear_overrides()


@pytest_asyncio.fixture
async def auth_client():
    from backend.api.v1.dependencies import get_current_user

    application.dependency_overrides[get_db_session] = _override_get_db
    _install_auth_override(get_current_user, _override_user_admin)

    async with AsyncClient(
        transport=ASGITransport(app=application),
        base_url="http://test",
    ) as ac:
        yield ac

    _clear_overrides()


@pytest_asyncio.fixture
async def readonly_client():
    from backend.api.v1.dependencies import get_current_user

    application.dependency_overrides[get_db_session] = _override_get_db
    _install_auth_override(get_current_user, _override_user_readonly)

    async with AsyncClient(
        transport=ASGITransport(app=application),
        base_url="http://test",
    ) as ac:
        yield ac

    _clear_overrides()