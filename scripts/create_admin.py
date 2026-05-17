"""
Utilitário para criação do primeiro usuário admin.
Uso: poetry run python scripts/create_admin.py
"""

import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.core.database import AsyncSessionFactory
from backend.schemas.user import UserCreate
from backend.domain.entities import UserProfile
from backend.services.user_service import UserService


async def main() -> None:
    matricula = input("Matrícula: ").strip()
    nome = input("Nome completo: ").strip()
    email = input("E-mail: ").strip()
    password = input("Senha (min 8 chars): ").strip()

    data = UserCreate(
        matricula=matricula,
        nome=nome,
        email=email,
        password=password,
        perfil=UserProfile.ADMIN,
    )

    async with AsyncSessionFactory() as session:
        service = UserService(session)
        user = await service.create(data)
        await session.commit()
        print(f"\nAdmin criado com sucesso: {user.matricula} ({user.email})")


if __name__ == "__main__":
    asyncio.run(main())
