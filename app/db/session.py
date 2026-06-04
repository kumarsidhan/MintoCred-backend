from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from sqlalchemy.pool import QueuePool

from app.core.config import settings


# ─── Base Model ──────────────────────────────────────────────────────────────
class Base(DeclarativeBase):
    pass


# ─── Engine ──────────────────────────────────────────────────────────────────
engine = create_engine(
    settings.DATABASE_URL,
    poolclass=QueuePool,
    pool_size=10,
    max_overflow=20,
    pool_recycle=1800,
    pool_pre_ping=True,
    echo=settings.DEBUG,
)


# ─── Force strict SQL mode & UTF8MB4 on every new connection ─────────────────
@event.listens_for(engine, "connect")
def set_connection_settings(dbapi_conn, _):
    cursor = dbapi_conn.cursor()
    cursor.execute("SET SESSION sql_mode='STRICT_TRANS_TABLES,NO_ZERO_DATE,ERROR_FOR_DIVISION_BY_ZERO'")
    cursor.execute("SET NAMES utf8mb4 COLLATE utf8mb4_unicode_ci")
    cursor.close()


# ─── Session Factory ─────────────────────────────────────────────────────────
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)


# ─── Dependency ──────────────────────────────────────────────────────────────
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ─── Create All Tables ───────────────────────────────────────────────────────
def init_db():
    """
    Import all models before calling create_all so SQLAlchemy
    knows about every table. Called once at app startup.
    """
    from app.models import user  # noqa: F401 — registers models with Base
    Base.metadata.create_all(bind=engine)
