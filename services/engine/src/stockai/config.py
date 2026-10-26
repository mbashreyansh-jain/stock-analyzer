"""Settings read from environment variables, with defaults for local development."""

import os
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]


def _load_dotenv() -> None:
    """Fill os.environ from the repo's .env file, without overriding values already set."""
    env_file = REPO_ROOT / ".env"
    if not env_file.exists():
        return
    for line in env_file.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip())


@dataclass(frozen=True)
class Settings:
    database_url: str
    raw_dir: Path
    nse_min_interval: float
    migrations_dir: Path
    web_dir: Path
    public_url: str
    cookie_secure: bool
    session_days: int
    gemini_api_key: str
    gemini_model: str


def get_settings() -> Settings:
    _load_dotenv()
    raw_dir = Path(os.environ.get("STOCKAI_RAW_DIR", "data/raw"))
    if not raw_dir.is_absolute():
        raw_dir = REPO_ROOT / raw_dir
    return Settings(
        database_url=os.environ.get("DATABASE_URL", "postgresql://stockai:stockai@localhost:5433/stockai"),
        raw_dir=raw_dir,
        nse_min_interval=float(os.environ.get("STOCKAI_NSE_MIN_INTERVAL", "0.4")),
        migrations_dir=REPO_ROOT / "db" / "migrations",
        web_dir=REPO_ROOT / "apps" / "web",
        public_url=os.environ.get("STOCKAI_PUBLIC_URL", "http://localhost:8000").rstrip("/"),
        cookie_secure=os.environ.get("STOCKAI_COOKIE_SECURE", "false").lower() in ("1", "true", "yes"),
        session_days=int(os.environ.get("STOCKAI_SESSION_DAYS", "30")),
        gemini_api_key=os.environ.get("GEMINI_API_KEY", ""),
        gemini_model=os.environ.get("GEMINI_MODEL", "gemini-2.5-flash"),
    )
