from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.core.config import get_settings


class Base(DeclarativeBase):
    pass


settings = get_settings()
connect_args = {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}
engine_kwargs = {"pool_pre_ping": True, "connect_args": connect_args}
# SQLite uses its native pool policy. PostgreSQL/enterprise engines receive bounded pool governance.
if not settings.database_url.startswith("sqlite"):
    engine_kwargs.update({
        "pool_size": max(1, int(settings.db_pool_size)),
        "max_overflow": max(0, int(settings.db_max_overflow)),
        "pool_timeout": max(1, int(settings.db_pool_timeout_seconds)),
        "pool_recycle": max(60, int(settings.db_pool_recycle_seconds)),
    })
engine = create_engine(settings.database_url, **engine_kwargs)

# v6.3.9 privacy-minimized SQL telemetry; never stores SQL text or bind values.
from app.core.db_performance import install_db_performance_instrumentation
install_db_performance_instrumentation(engine)

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def get_db():
    db = SessionLocal()
    # API-originating writes participate in v6.3.10 transactional read-model invalidation.
    db.info["mgc_read_model_invalidation_enabled"] = True
    try:
        yield db
    finally:
        db.close()


# v6.3.20 authoritative write fencing. This is a second line of defence behind the
# HTTP middleware and also covers Celery/maintenance sessions. The check runs before
# commit so an unsafe transaction is rolled back rather than committed to an unproven
# primary/evidence generation.
from sqlalchemy import event

def _authoritative_write_fence_enabled() -> bool:
    cfg = get_settings()
    return bool(getattr(cfg, "authoritative_write_fence_enabled", True)) and (
        bool(getattr(cfg, "database_ha_enabled", False)) or bool(getattr(cfg, "evidence_ha_enabled", False))
    )

def _assert_authoritative_session_write_safe(session) -> None:
    if not _authoritative_write_fence_enabled():
        return
    from app.core.authoritative_ha import assert_authoritative_write_safe
    # Use the same physical/transactional DB connection that will perform the write.
    assert_authoritative_write_safe(connection=session.connection())

@event.listens_for(SessionLocal.class_, "before_flush")
def _authoritative_write_fence_before_flush(session, flush_context, instances):
    if session.new or session.dirty or session.deleted:
        _assert_authoritative_session_write_safe(session)

@event.listens_for(SessionLocal.class_, "do_orm_execute")
def _authoritative_write_fence_bulk_orm(orm_execute_state):
    if orm_execute_state.is_update or orm_execute_state.is_delete:
        _assert_authoritative_session_write_safe(orm_execute_state.session)

@event.listens_for(SessionLocal.class_, "before_commit")
def _authoritative_write_fence_before_commit(session):
    # Final fence also covers raw SQL mutation followed by Session.commit(), where ORM
    # dirty/new/deleted collections may not expose the write to before_flush.
    _assert_authoritative_session_write_safe(session)
