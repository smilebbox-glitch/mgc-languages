"""Database engine and session bootstrap for MGC Languages.

This module owns URL normalization and SQLAlchemy engine/session construction.
ORM models and query telemetry remain in the legacy app module for now and will
be extracted in later compatibility-preserving increments.
"""

from __future__ import annotations

import os
from typing import Any

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from mgc.config import (
    DATABASE_URL as CONFIG_DATABASE_URL,
    DB_CONNECT_TIMEOUT_SECONDS,
    DB_MAX_OVERFLOW,
    DB_POOL_SIZE,
    DB_STATEMENT_TIMEOUT_MS,
)


def normalize_database_url(value: str) -> str:
    """Normalize common PostgreSQL URLs to the psycopg v3 SQLAlchemy dialect."""
    url = value
    if url.startswith("postgres://"):
        return url.replace("postgres://", "postgresql+psycopg://", 1)
    if url.startswith("postgresql://") and "+psycopg" not in url:
        return url.replace("postgresql://", "postgresql+psycopg://", 1)
    return url


DATABASE_URL = normalize_database_url(CONFIG_DATABASE_URL)

connect_args = (
    {"check_same_thread": False}
    if DATABASE_URL.startswith("sqlite")
    else {
        "connect_timeout": DB_CONNECT_TIMEOUT_SECONDS,
        "options": f"-c statement_timeout={DB_STATEMENT_TIMEOUT_MS}",
    }
)

engine_kwargs: dict[str, Any] = {
    "pool_pre_ping": True,
    "connect_args": connect_args,
}
if not DATABASE_URL.startswith("sqlite"):
    engine_kwargs.update(
        {
            "pool_size": DB_POOL_SIZE,
            "max_overflow": DB_MAX_OVERFLOW,
            "pool_timeout": max(1, int(os.getenv("DB_POOL_TIMEOUT", "30"))),
            "pool_recycle": max(60, int(os.getenv("DB_POOL_RECYCLE", "1800"))),
        }
    )

engine = create_engine(DATABASE_URL, **engine_kwargs)
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)
