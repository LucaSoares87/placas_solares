import pytest
from httpx import AsyncClient

from backend.core.security import create_access_token


def _auth_header(matricula: str = "MAT001", perfil: str = "engenharia") -> dict:
    token = create_access_token(subject=matricula, extra_claims={"perfil": perfil})
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_create_transformer_and_uc(client: AsyncClient, db_session):
    from backend.models.user import AuthorizedUser
    from backend.services.user_service import hash_password

    user = AuthorizedUser(
        matricula="MAT001",
        nome="Engenheiro Teste",
        email="eng@test.com",
        hashed_password=hash_password("senha12345"),
        perfil="engenharia",
        ativo=True,
    )
    db_session.add(user)
    await db_session.flush()

    headers = _auth_header()

    tr_response = await client.post(
        "/api/v1/transformers",
        json={
            "transformer_id": "TR-TEST-001",
            "latitude": -8.034,
            "longitude": -34.941,
            "rated_kva": 75.0,
            "substation": "SE-NORTE",
            "feeder": "AL-01",
        },
        headers=headers,
    )
    assert tr_response.status_code == 200
    assert tr_response.json()["data"]["transformer_id"] == "TR-TEST-001"

    uc_response = await client.post(
        "/api/v1/consumer-units",
        json={
            "uc_code": "UC-TEST-001",
            "transformer_id": "TR-TEST-001",
            "latitude": -8.035,
            "longitude": -34.942,
            "profile": "residential",
            "is_telemetered": False,
            "has_gd": True,
            "gd_installed_kwp": 5.2,
        },
        headers=headers,
    )
    assert uc_response.status_code == 200
    assert uc_response.json()["data"]["uc_code"] == "UC-TEST-001"

    get_response = await client.get("/api/v1/consumer-units/UC-TEST-001", headers=headers)
    assert get_response.status_code == 200
    assert get_response.json()["data"]["has_gd"] is True


@pytest.mark.asyncio
async def test_get_transformer_not_found(client: AsyncClient, db_session):
    from backend.models.user import AuthorizedUser
    from backend.services.user_service import hash_password

    user = AuthorizedUser(
        matricula="MAT002",
        nome="Consulta Teste",
        email="consulta@test.com",
        hashed_password=hash_password("senha12345"),
        perfil="consulta",
        ativo=True,
    )
    db_session.add(user)
    await db_session.flush()

    headers = _auth_header("MAT002", "consulta")
    response = await client.get("/api/v1/transformers/TR-NAO-EXISTE", headers=headers)
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_list_consumer_units_pagination(client: AsyncClient, db_session):
    from backend.models.user import AuthorizedUser
    from backend.services.user_service import hash_password

    user = AuthorizedUser(
        matricula="MAT003",
        nome="Admin Teste",
        email="admin@test.com",
        hashed_password=hash_password("senha12345"),
        perfil="admin",
        ativo=True,
    )
    db_session.add(user)
    await db_session.flush()

    headers = _auth_header("MAT003", "admin")
    response = await client.get("/api/v1/consumer-units?page=1&page_size=10", headers=headers)
    assert response.status_code == 200
    body = response.json()
    assert "data" in body
    assert "total" in body
    assert "pages" in body
