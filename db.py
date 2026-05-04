import os
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, declarative_base, sessionmaker

_BACKEND_DIR = Path(__file__).resolve().parent
_PROJECT_ROOT = _BACKEND_DIR.parent
# Project root (.env) phir backend/.env — taake uvicorn cwd `Cartify-backend` ho ya reload subprocess ho
load_dotenv(_PROJECT_ROOT / ".env")
load_dotenv(_BACKEND_DIR / ".env", override=True)

DB_POOL_PRE_PING = os.getenv("DB_POOL_PRE_PING", "true").lower() == "true"
DB_POOL_RECYCLE = int(os.getenv("DB_POOL_RECYCLE", "300"))
DB_SSLMODE = os.getenv("DB_SSLMODE", "require").strip() or "require"

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
    _creds = DATABASE_URL.split("@", 1)[0] if "@" in DATABASE_URL else DATABASE_URL
    if "project-ref" in _creds.lower() or ("<" in _creds and ">" in _creds):
        raise RuntimeError(
            "DATABASE_URL mein abhi placeholder username hai (jaise postgres.<project-ref>). "
            "Supabase Dashboard → Project Settings → Database se poori **URI copy** karo; "
            "username `postgres.<tumhara_asli_ref>` hona chahiye — angle brackets wala template nahi."
        )

if DATABASE_URL.startswith("sqlite"):
    engine = create_engine(
        DATABASE_URL,
        connect_args={"check_same_thread": False},
    )
else:
    engine = create_engine(
        DATABASE_URL,
        pool_pre_ping=DB_POOL_PRE_PING,
        pool_recycle=DB_POOL_RECYCLE,
        connect_args={"sslmode": DB_SSLMODE},
    )
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
Base = declarative_base()


def get_db() -> Session:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
