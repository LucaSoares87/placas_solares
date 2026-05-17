from unittest.mock import AsyncMock, MagicMock

import pytest

from backend.core.exceptions import ConflictException, EntityNotFoundException
from backend.domain.entities import UCProfile, UserProfile
from backend.schemas.consumer_unit import ConsumerUnitCreate
from backend.schemas.user import UserCreate
from backend.services.consumer_unit_service import ConsumerUnitService
from backend.services.user_service import UserService, hash_password, verify_password


def test_hash_and_verify_password():
    raw = "senha_segura_123"
    hashed = hash_password(raw)
    assert hashed != raw
    assert verify_password(raw, hashed)
    assert not verify_password("errada", hashed)


@pytest.mark.asyncio
async def test_user_service_create_conflict():
    session = MagicMock()
    service = UserService(session)
    service._repo = MagicMock()
    service._repo.get_by_matricula = AsyncMock(return_value=MagicMock())

    with pytest.raises(ConflictException):
        await service.create(
            UserCreate(
                matricula="MAT001",
                nome="Test User",
                email="test@test.com",
                password="senha12345",
                perfil=UserProfile.READONLY,
            )
        )


@pytest.mark.asyncio
async def test_user_service_get_not_found():
    session = MagicMock()
    service = UserService(session)
    service._repo = MagicMock()
    service._repo.get_by_matricula = AsyncMock(return_value=None)

    with pytest.raises(EntityNotFoundException):
        await service.get_by_matricula("NAO_EXISTE")


@pytest.mark.asyncio
async def test_consumer_unit_service_duplicate():
    session = MagicMock()
    service = ConsumerUnitService(session)
    service._uc_repo = MagicMock()
    service._tr_repo = MagicMock()
    service._uc_repo.exists_by_uc_code = AsyncMock(return_value=True)

    with pytest.raises(ConflictException):
        await service.create(
            ConsumerUnitCreate(
                uc_code="UC001",
                transformer_id="TR-001",
                latitude=-8.034,
                longitude=-34.941,
                profile=UCProfile.RESIDENTIAL,
            )
        )


@pytest.mark.asyncio
async def test_consumer_unit_service_transformer_not_found():
    session = MagicMock()
    service = ConsumerUnitService(session)
    service._uc_repo = MagicMock()
    service._tr_repo = MagicMock()
    service._uc_repo.exists_by_uc_code = AsyncMock(return_value=False)
    service._tr_repo.exists_by_transformer_id = AsyncMock(return_value=False)

    with pytest.raises(EntityNotFoundException):
        await service.create(
            ConsumerUnitCreate(
                uc_code="UC002",
                transformer_id="TR-NAO-EXISTE",
                latitude=-8.034,
                longitude=-34.941,
                profile=UCProfile.RESIDENTIAL,
            )
        )
