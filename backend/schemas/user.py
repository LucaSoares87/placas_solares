from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, Field

from backend.domain.entities import UserProfile


class UserCreate(BaseModel):
    matricula: str = Field(..., min_length=3, max_length=20)
    nome: str = Field(..., min_length=2, max_length=120)
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)
    perfil: UserProfile = UserProfile.READONLY


class UserUpdate(BaseModel):
    nome: Optional[str] = Field(None, min_length=2, max_length=120)
    email: Optional[EmailStr] = None
    password: Optional[str] = Field(None, min_length=8, max_length=128)
    perfil: Optional[UserProfile] = None


class UserRead(BaseModel):
    id: int
    matricula: str
    nome: str
    email: str
    perfil: UserProfile
    ativo: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class UserReadPublic(BaseModel):
    matricula: str
    nome: str
    perfil: UserProfile
    ativo: bool

    model_config = {"from_attributes": True}


class LoginRequest(BaseModel):
    matricula: str = Field(..., min_length=3, max_length=20)
    password: str = Field(..., min_length=8, max_length=128)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserReadPublic
