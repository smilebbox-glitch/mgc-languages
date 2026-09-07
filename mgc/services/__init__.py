"""Business service layer for the modular MGC Languages runtime."""

from .terminology import TerminologyServiceBindings, build_terminology_service
from .users import UserServiceBindings, build_user_service

__all__ = [
    "UserServiceBindings",
    "build_user_service",
    "TerminologyServiceBindings",
    "build_terminology_service",
]
