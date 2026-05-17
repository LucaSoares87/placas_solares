import structlog
from passlib.context import CryptContext
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.exceptions import ConflictException, EntityNotFoundException, ValidationException
from backend.models.user import AuthorizedUser
from backend.repositories.user_repository import UserRepository
from backend.schemas.user import UserCreate, UserUpdate

logger = structlog.get_logger(__name__)

_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    return _pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return _pwd_context.verify(plain, hashed)


class UserService:
    def __init__(self, session: AsyncSession) -> None:
        self._repo = UserRepository(session)

    async def create(self, data: UserCreate) -> AuthorizedUser:
        if await self._repo.get_by_matricula(data.matricula):
            raise ConflictException(
                message=f"Matrícula {data.matricula} já cadastrada.",
                details={"matricula": data.matricula},
            )

        if await self._repo.get_by_email(data.email):
            raise ConflictException(
                message=f"E-mail {data.email} já cadastrado.",
                details={"email": data.email},
            )

        user = AuthorizedUser(
            matricula=data.matricula,
            nome=data.nome,
            email=data.email,
            hashed_password=hash_password(data.password),
            perfil=data.perfil,
            ativo=True,
        )
        saved = await self._repo.save(user)
        logger.info("user.created", matricula=data.matricula, perfil=data.perfil)
        return saved

    async def get_by_matricula(self, matricula: str) -> AuthorizedUser:
        user = await self._repo.get_by_matricula(matricula)
        if not user:
            raise EntityNotFoundException(
                message=f"Usuário {matricula} não encontrado.",
                details={"matricula": matricula},
            )
        return user

    async def authenticate(self, matricula: str, password: str) -> AuthorizedUser:
        user = await self._repo.get_active_by_matricula(matricula)
        if not user or not verify_password(password, user.hashed_password):
            raise ValidationException(
                message="Credenciais inválidas.",
                code="INVALID_CREDENTIALS",
            )
        return user

    async def update(self, matricula: str, data: UserUpdate) -> AuthorizedUser:
        user = await self.get_by_matricula(matricula)
        update_data = data.model_dump(exclude_none=True)

        if "password" in update_data:
            update_data["hashed_password"] = hash_password(update_data.pop("password"))

        for field, value in update_data.items():
            setattr(user, field, value)

        saved = await self._repo.save(user)
        logger.info("user.updated", matricula=matricula)
        return saved

    async def deactivate(self, matricula: str) -> AuthorizedUser:
        user = await self.get_by_matricula(matricula)
        user.ativo = False
        saved = await self._repo.save(user)
        logger.info("user.deactivated", matricula=matricula)
        return saved

    async def list_paginated(
        self, offset: int = 0, limit: int = 20
    ) -> tuple[list[AuthorizedUser], int]:
        items = await self._repo.list_active(offset, limit)
        total = await self._repo.count_all()
        return items, total
