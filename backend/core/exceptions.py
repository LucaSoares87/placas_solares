from dataclasses import dataclass, field
from typing import Any


@dataclass
class DomainException(Exception):
    message: str
    code: str = "DOMAIN_ERROR"
    details: dict[str, Any] = field(default_factory=dict)

    def __str__(self) -> str:
        return self.message


@dataclass
class EntityNotFoundException(DomainException):
    code: str = "NOT_FOUND"


@dataclass
class ValidationException(DomainException):
    code: str = "VALIDATION_ERROR"


@dataclass
class UnauthorizedException(DomainException):
    code: str = "UNAUTHORIZED"


@dataclass
class ForbiddenException(DomainException):
    code: str = "FORBIDDEN"


@dataclass
class ConflictException(DomainException):
    code: str = "CONFLICT"


@dataclass
class InferenceException(DomainException):
    code: str = "INFERENCE_ERROR"


@dataclass
class ExternalServiceException(DomainException):
    code: str = "EXTERNAL_SERVICE_ERROR"
    service: str = ""
