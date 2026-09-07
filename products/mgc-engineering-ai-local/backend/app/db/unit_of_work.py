from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from sqlalchemy.orm import Session
from sqlalchemy.orm.exc import StaleDataError


@dataclass
class EditConflict(RuntimeError):
    entity_type: str
    entity_id: str
    expected_version: int | None = None
    current_version: int | None = None
    current_record: dict | None = None

    def __str__(self) -> str:
        return f"Concurrent edit conflict for {self.entity_type} {self.entity_id}"


def _conflict_record(row) -> dict:
    payload = {}
    table = getattr(row, "__table__", None)
    if table is None:
        return payload
    for column in table.columns:
        value = getattr(row, column.name)
        if isinstance(value, datetime):
            value = value.isoformat()
        payload[column.name] = value
    return payload


def require_expected_version(row, expected_version: int | None, entity_type: str) -> None:
    if expected_version is None:
        return
    current = int(getattr(row, "row_version", 1) or 1)
    if int(expected_version) != current:
        raise EditConflict(entity_type, str(getattr(row, "id", "")), int(expected_version), current, _conflict_record(row))


class UnitOfWork:
    """Small SQLAlchemy transaction boundary for domain record + audit/event atomicy.

    Reads may have already autobegun the Session; therefore this wrapper deliberately
    commits the existing transaction rather than nesting a new `Session.begin()`.
    """
    def __init__(self, db: Session):
        self.db = db

    def __enter__(self):
        return self

    def commit(self) -> None:
        try:
            self.db.flush()
            self.db.commit()
        except StaleDataError as exc:
            self.db.rollback()
            raise EditConflict("versioned_record", "unknown") from exc
        except Exception:
            self.db.rollback()
            raise

    def __exit__(self, exc_type, exc, tb):
        if exc_type is not None:
            self.db.rollback()
        return False
