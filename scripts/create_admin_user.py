import asyncio
import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.core.database import AsyncSessionFactory  # noqa: E402
from backend.repositories.user_repository import UserRepository  # noqa: E402
from backend.schemas.user import UserCreate  # noqa: E402
from backend.services.user_service import UserService  # noqa: E402


DEFAULT_MATRICULA = "ADMIN001"
DEFAULT_NOME = "Administrador"
DEFAULT_EMAIL = "admin@local.com"
DEFAULT_PASSWORD = "Admin12345"
DEFAULT_PERFIL = "admin"


async def main() -> None:
    matricula = os.getenv("ADMIN_MATRICULA", DEFAULT_MATRICULA)
    nome = os.getenv("ADMIN_NOME", DEFAULT_NOME)
    email = os.getenv("ADMIN_EMAIL", DEFAULT_EMAIL)
    password = os.getenv("ADMIN_PASSWORD", DEFAULT_PASSWORD)
    perfil = os.getenv("ADMIN_PERFIL", DEFAULT_PERFIL)

    async with AsyncSessionFactory() as session:
        repo = UserRepository(session)
        service = UserService(session)

        existing = await repo.get_by_matricula(matricula)
        if existing:
            print(f"Usuario ja existe: {existing.matricula}")
            return

        user = await service.create(
            UserCreate(
                matricula=matricula,
                nome=nome,
                email=email,
                password=password,
                perfil=perfil,
            )
        )

        await session.commit()

        print("Usuario admin criado com sucesso.")
        print(f"Matricula: {user.matricula}")
        print(f"Email: {user.email}")
        print(f"Perfil: {user.perfil}")


if __name__ == "__main__":
    asyncio.run(main())