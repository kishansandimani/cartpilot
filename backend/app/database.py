from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from .config import get_settings

_settings = get_settings()
# Render/Heroku give "postgres://..."; SQLAlchemy needs "postgresql://..."
if _settings.database_url.startswith("postgres://"):
    _settings.database_url = "postgresql://" + _settings.database_url[len("postgres://"):]

_is_sqlite = _settings.database_url.startswith("sqlite")
_connect_args = {"check_same_thread": False, "timeout": 30} if _is_sqlite else {}
engine = create_engine(_settings.database_url, connect_args=_connect_args, pool_pre_ping=True)

if _is_sqlite:
    @event.listens_for(engine, "connect")
    def _sqlite_settings(dbapi_conn, _record):
        cur = dbapi_conn.cursor()
        cur.execute("PRAGMA journal_mode=WAL")      # readers no longer block the writer
        cur.execute("PRAGMA busy_timeout=30000")    # wait up to 30s instead of failing at once
        cur.close()

SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """Creates tables that do not exist yet. (For schema changes later, add Alembic.)"""
    from . import models  # noqa: F401  (registers the tables)
    Base.metadata.create_all(bind=engine)