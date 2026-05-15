import os
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.pool import NullPool

Base = declarative_base()

_engine = None
_SessionLocal = None
_engine_url = None

BACKEND_ROOT = Path(__file__).resolve().parents[2]
PROJECT_ROOT = BACKEND_ROOT.parent


def _resolve_database_url() -> str:
    configured_url = os.getenv("APP_DATABASE_URL")
    if not configured_url:
        default_path = (PROJECT_ROOT / "business_analysis.db").resolve()
        return f"sqlite:///{default_path.as_posix()}"

    url = configured_url
    if not url.startswith("sqlite:///") or url == "sqlite:///:memory:":
        return url

    db_path = url.removeprefix("sqlite:///")
    path = Path(db_path)
    if path.is_absolute():
        return url
    return f"sqlite:///{path.resolve().as_posix()}"


def get_engine():
    global _engine, _SessionLocal, _engine_url
    url = _resolve_database_url()
    if _engine is None or _engine_url != url:
        if _engine is not None:
            _engine.dispose()
        _engine = create_engine(url, connect_args={"check_same_thread": False}, poolclass=NullPool)
        _SessionLocal = None
        _engine_url = url
    return _engine


def get_session():
    global _SessionLocal
    if _SessionLocal is None:
        _SessionLocal = sessionmaker(bind=get_engine())
    return _SessionLocal()


def init_db():
    from app.projects import models  # noqa: F401
    Base.metadata.create_all(bind=get_engine())
    _ensure_sqlite_project_columns()


def _ensure_sqlite_project_columns():
    url = _resolve_database_url()
    if not url.startswith("sqlite:///") or url == "sqlite:///:memory:":
        return

    engine = get_engine()
    with engine.begin() as conn:
        rows = conn.exec_driver_sql("PRAGMA table_info(projects)").fetchall()
        if not rows:
            return
        existing_columns = {row[1] for row in rows}
        if "is_test" not in existing_columns:
            conn.exec_driver_sql("ALTER TABLE projects ADD COLUMN is_test INTEGER NOT NULL DEFAULT 0")
        if "data_source_path" not in existing_columns:
            conn.exec_driver_sql("ALTER TABLE projects ADD COLUMN data_source_path VARCHAR(1024)")


def reset_engine():
    global _engine, _SessionLocal, _engine_url
    if _engine is not None:
        _engine.dispose()
    _engine = None
    _SessionLocal = None
    _engine_url = None
