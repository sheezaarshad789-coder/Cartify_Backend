import os
import logging
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, declarative_base, sessionmaker

_BACKEND_DIR = Path(__file__).resolve().parent
_PROJECT_ROOT = _BACKEND_DIR.parent
# Project root (.env) phir backend/.env — taake uvicorn cwd `Cartify-backend` ho ya reload subprocess ho
load_dotenv(_PROJECT_ROOT / ".env")
load_dotenv(_BACKEND_DIR / ".env", override=True)

DB_POOL_PRE_PING = os.getenv("DB_POOL_PRE_PING", "true").lower() == "true"
DB_POOL_RECYCLE = int(os.getenv("DB_POOL_RECYCLE", "300"))
DB_SSLMODE = os.getenv("DB_SSLMODE", "require").strip() or "require"
DB_AUTO_SQLITE_FALLBACK = os.getenv("CARTIFY_AUTO_SQLITE_FALLBACK", "true").lower() in ("1", "true", "yes")
logger = logging.getLogger("cartify_db")

# Local smoke test: real Supabase ki zaroorat nahi (API + /health verify karne ke liye)
DEV_SQLITE_MODE = os.getenv("CARTIFY_DEV_SQLITE", "").strip().lower() in ("1", "true", "yes")
if DEV_SQLITE_MODE:
    _sqlite_file = _BACKEND_DIR / "cartify_dev.db"
    DATABASE_URL = f"sqlite:///{_sqlite_file.as_posix()}"
else:
    DATABASE_URL = os.getenv("DATABASE_URL", "").strip()
    if not DATABASE_URL:
        raise RuntimeError(
            "DATABASE_URL is required. Set your Supabase Postgres connection string in backend/.env."
        )
    if ("supabase.co" not in DATABASE_URL) and ("supabase.com" not in DATABASE_URL):
        raise RuntimeError(
            "Supabase-only setup is enabled. DATABASE_URL must point to a Supabase host (.supabase.co or .supabase.com)."
        )

def _build_sqlite_engine():
    return create_engine(
        DATABASE_URL,
        connect_args={"check_same_thread": False},
    )


def _build_postgres_engine(url: str):
    return create_engine(
        url,
        pool_pre_ping=DB_POOL_PRE_PING,
        pool_recycle=DB_POOL_RECYCLE,
        connect_args={"sslmode": DB_SSLMODE},
    )


if DATABASE_URL.startswith("sqlite"):
    engine = _build_sqlite_engine()
else:
    engine = _build_postgres_engine(DATABASE_URL)
    if DB_AUTO_SQLITE_FALLBACK:
        try:
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
        except Exception as exc:
            DEV_SQLITE_MODE = True
            _sqlite_file = _BACKEND_DIR / "cartify_dev.db"
            DATABASE_URL = f"sqlite:///{_sqlite_file.as_posix()}"
            logger.warning(
                "Postgres unavailable (%s). Falling back to local SQLite because CARTIFY_AUTO_SQLITE_FALLBACK is enabled.",
                exc,
            )
            engine = _build_sqlite_engine()
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
Base = declarative_base()


def get_db() -> Session:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
