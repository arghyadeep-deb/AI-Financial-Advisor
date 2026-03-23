import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# Project root = AI ADVISORY/
BASE_DIR = Path(__file__).parent.parent.parent


class Config:

    # ── Database ──────────────────────────────────────────────────────────
    DATABASE_URL = os.getenv(
        "DATABASE_URL",
        f"sqlite:///{BASE_DIR}/advisor.db"
    )

    # ── Auth ──────────────────────────────────────────────────────────────
    SECRET_KEY        = os.getenv("SECRET_KEY", "changeme")
    ALGORITHM         = "HS256"
    TOKEN_EXPIRE_DAYS = 7

    # ── LLM Keys ──────────────────────────────────────────────────────────
    GROQ_KEYS = [
        os.getenv("GROQ_API_KEY_1"),
        os.getenv("GROQ_API_KEY_2"),
        os.getenv("GROQ_API_KEY_3"),
        os.getenv("GROQ_API_KEY_4"),
    ]
    GROQ_KEYS = [k for k in GROQ_KEYS if k]

    GOOGLE_KEYS = [
        os.getenv("GOOGLE_API_KEY_1"),
        os.getenv("GOOGLE_API_KEY_2"),
        os.getenv("GOOGLE_API_KEY_3"),
        os.getenv("GOOGLE_API_KEY_4"),
    ]
    GOOGLE_KEYS = [k for k in GOOGLE_KEYS if k]

    OPENROUTER_KEY = os.getenv("OPENROUTER_API_KEY")

    # ── Paths (all shared folders are at project root) ────────────────────
    KB_DIR            = BASE_DIR / "knowledge_base"
    DATA_SOURCES_DIR  = BASE_DIR / "data_sources"
    CACHE_DIR         = BASE_DIR / ".cache"

    # ── API ───────────────────────────────────────────────────────────────
    API_HOST = "0.0.0.0"
    API_PORT = 8000
    FRONTEND_URL = "http://localhost:8501"


config = Config()