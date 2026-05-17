from sqlalchemy import Boolean, String
from sqlalchemy.orm import Mapped, mapped_column

from backend.core.database import Base
from backend.models.base_model import TimestampMixin


class AuthorizedUser(Base, TimestampMixin):
    __tablename__ = "authorized_users"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    matricula: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    nome: Mapped[str] = mapped_column(String(120), nullable=False)
    email: Mapped[str] = mapped_column(String(200), unique=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(256), nullable=False)
    perfil: Mapped[str] = mapped_column(String(30), nullable=False, default="consulta")
    ativo: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    def __repr__(self) -> str:
        return f"<AuthorizedUser matricula={self.matricula} perfil={self.perfil}>"