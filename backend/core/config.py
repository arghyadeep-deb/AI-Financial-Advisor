"""Application configuration (T108 / F001-FR12).

Secrets have no usable fallback in production: ``Config.validate()`` is called
at startup and raises ``ConfigError`` for a missing, placeholder or short
signing key.  Development and test modes may use an explicitly generated
ephemeral key, never a constant shared across installs.
"""
import os
import secrets
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

# Project root = AI ADVISORY/
BASE_DIR = Path(__file__).parent.parent.parent

_PLACEHOLDER_SECRETS = {
    "", "changeme", "changeme-in-production", "secret", "password",
    "your-secret-key", "your_secret_key", "replace-me", "replace_me", "test",
}
MIN_SECRET_LENGTH = 32


class ConfigError(RuntimeError):
    """Raised when configuration is unsafe for the selected APP_ENV."""


def _int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, default))
    except (TypeError, ValueError):
        return default


class Config:
    TAX_SANDBOX_ENABLED = os.getenv("TAX_SANDBOX_ENABLED", "false").strip().lower() == "true"
    SYNTHETIC_MANUAL_CASH_ENABLED = os.getenv('SYNTHETIC_MANUAL_CASH_ENABLED', 'false').lower() == 'true'
    SYNTHETIC_HOUSEHOLDS_ENABLED = os.getenv('SYNTHETIC_HOUSEHOLDS_ENABLED', 'false').lower() == 'true'

    MAIL_PROVIDER = os.getenv('MAIL_PROVIDER', 'fake')
    MAIL_LIVE_ENABLED = os.getenv('MAIL_LIVE_ENABLED', 'false').lower() == 'true'
    RESEND_API_KEY = os.getenv('RESEND_API_KEY', '')
    MAIL_FROM = os.getenv('MAIL_FROM', '')
    MAIL_DAILY_LIMIT = _int('MAIL_DAILY_LIMIT', 100)
    NOTIFICATION_EMAIL_ENABLED = os.getenv('NOTIFICATION_EMAIL_ENABLED', 'false').lower() == 'true'
    MFA_REQUIRED = os.getenv('MFA_REQUIRED', 'false').lower() == 'true'
    RECEIPT_SOURCE_LIMIT = _int('RECEIPT_SOURCE_LIMIT', 10)
    RECEIPT_GLOBAL_LIMIT = _int('RECEIPT_GLOBAL_LIMIT', 1000)
    RECEIPT_WINDOW_SECONDS = _int('RECEIPT_WINDOW_SECONDS', 900)

    # Offline controls. No implicit key, journal location, or real-data opt-in.
    ANALYSIS_DAILY_LIMIT = _int("ANALYSIS_DAILY_LIMIT", 100)
    CHAT_DAILY_LIMIT = _int("CHAT_DAILY_LIMIT", 200)
    UPLOAD_DAILY_LIMIT = _int("UPLOAD_DAILY_LIMIT", 20)
    STORAGE_DAILY_BYTES = _int("STORAGE_DAILY_BYTES", 50 * 1024 * 1024)
    SUPPRESSION_JOURNAL = os.getenv("SUPPRESSION_JOURNAL", "")
    PRIVATE_STORAGE_ROOT = os.getenv("PRIVATE_STORAGE_ROOT", "")
    STORAGE_KEYS_JSON = os.getenv("STORAGE_KEYS_JSON", "{}")
    STORAGE_ACTIVE_KEY = os.getenv("STORAGE_ACTIVE_KEY", "")
    SOURCE_RETENTION_DAYS = _int("SOURCE_RETENTION_DAYS", 30)
    EXPORT_TTL_SECONDS = _int("EXPORT_TTL_SECONDS", 300)
    EXPORT_DAILY_LIMIT = _int("EXPORT_DAILY_LIMIT", 10)
    BACKUP_RETENTION_DAYS = _int("BACKUP_RETENTION_DAYS", 30)
    SYNTHETIC_STATEMENTS_ENABLED = os.getenv("SYNTHETIC_STATEMENTS_ENABLED", "false").lower() == "true"
    STATEMENT_MAX_BYTES = _int("STATEMENT_MAX_BYTES", 1024 * 1024)
    STATEMENT_MAX_ROWS = _int("STATEMENT_MAX_ROWS", 10000)
    STATEMENT_TIMEOUT_SECONDS = _int("STATEMENT_TIMEOUT_SECONDS", 5)
    RETENTION_INTERVAL_SECONDS = _int("RETENTION_INTERVAL_SECONDS", 3600)
    WORKER_STALE_SECONDS = _int("WORKER_STALE_SECONDS", 300)
    SOURCE_STORAGE_LIMIT_BYTES = _int("SOURCE_STORAGE_LIMIT_BYTES", 100 * 1024 * 1024)
    MODEL_DAILY_COST_PAISE = _int("MODEL_DAILY_COST_PAISE", 0)
    MODEL_DAILY_TOKEN_LIMIT = _int("MODEL_DAILY_TOKEN_LIMIT", 0)
    GLOBAL_MODEL_DAILY_COST_PAISE = _int("GLOBAL_MODEL_DAILY_COST_PAISE", 0)

    # ── Environment ───────────────────────────────────────────────────────
    # production | staging | development | test.  Unknown values are treated
    # as production so a typo can never weaken the checks.
    APP_ENV = os.getenv("APP_ENV", "development").strip().lower()

    # ── Database ──────────────────────────────────────────────────────────
    DATABASE_URL = os.getenv(
        "DATABASE_URL",
        f"sqlite:///{(BASE_DIR / 'advisor.db').as_posix()}"
    )

    # ── Auth ──────────────────────────────────────────────────────────────
    # SECRET_KEY signs access tokens only.  It is never used to hash passwords.
    SECRET_KEY        = os.getenv("SECRET_KEY", "")
    # Previous signing keys still accepted for verification during rotation
    # (comma separated).  Tokens are always issued with SECRET_KEY.
    SECRET_KEY_PREVIOUS = [k for k in os.getenv("SECRET_KEY_PREVIOUS", "").split(",") if k.strip()]
    # The historical HMAC secret.  Needed only to verify legacy password
    # hashes once; a successful login rehashes with Argon2id.
    LEGACY_PASSWORD_SECRET = os.getenv("LEGACY_PASSWORD_SECRET", os.getenv("SECRET_KEY", ""))
    ALGORITHM         = "HS256"
    TOKEN_ISSUER      = os.getenv("TOKEN_ISSUER", "ai-advisory")
    TOKEN_AUDIENCE    = os.getenv("TOKEN_AUDIENCE", "ai-advisory-api")
    ACCESS_TOKEN_MINUTES = _int("ACCESS_TOKEN_MINUTES", 60)
    PASSWORD_RESET_MINUTES = _int("PASSWORD_RESET_MINUTES", 30)
    MIN_PASSWORD_LENGTH = _int("MIN_PASSWORD_LENGTH", 10)

    # Login protection
    LOGIN_MAX_FAILURES   = _int("LOGIN_MAX_FAILURES", 5)
    LOGIN_WINDOW_SECONDS = _int("LOGIN_WINDOW_SECONDS", 900)
    LOGIN_LOCK_SECONDS   = _int("LOGIN_LOCK_SECONDS", 900)

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

    # Hard bound on one model call (seconds) so a cold/unavailable provider
    # cannot hang a request indefinitely.
    LLM_TIMEOUT_SECONDS = _int("LLM_TIMEOUT_SECONDS", 30)
    LLM_MAX_ATTEMPTS    = _int("LLM_MAX_ATTEMPTS", 2)

    # ── Observability ─────────────────────────────────────────────────────
    # Raw prompt/response tracing is OFF unless explicitly enabled.  Even when
    # enabled, only the metadata allow-list in backend/core/telemetry.py is sent.
    TRACING_ENABLED = os.getenv("TELEMETRY_EXPORT_ENABLED", "false").strip().lower() == "true"

    # ── Paths (all shared folders are at project root) ────────────────────
    KB_DIR            = BASE_DIR / "knowledge_base"
    DATA_SOURCES_DIR  = BASE_DIR / "data_sources"
    CACHE_DIR         = BASE_DIR / ".cache"

    # ── API ───────────────────────────────────────────────────────────────
    API_HOST = os.getenv("API_HOST", "127.0.0.1")
    API_PORT = _int("API_PORT", 8000)
    FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:8000")
    CORS_ORIGINS = [o.strip() for o in os.getenv("CORS_ORIGINS", FRONTEND_URL).split(",") if o.strip()]

    # ── helpers ───────────────────────────────────────────────────────────
    @property
    def is_production_like(self) -> bool:
        return self.APP_ENV not in {"development", "dev", "test", "local"}

    def validate(self) -> None:
        """Refuse to start with an unsafe configuration.

        Production-like environments require a strong signing key.  In
        development/test a missing key is replaced by a per-process random key
        (tokens do not survive restart) and a warning is logged by the caller.
        """
        key = self.SECRET_KEY
        if self.MAIL_PROVIDER not in {'fake', 'resend'} or not 0 <= self.MAIL_DAILY_LIMIT <= 100:
            raise ConfigError('Invalid mail provider or daily cap')
        if not (1 <= self.RECEIPT_SOURCE_LIMIT <= self.RECEIPT_GLOBAL_LIMIT <= 10**6 and 1 <= self.RECEIPT_WINDOW_SECONDS <= 86400):
            raise ConfigError('Invalid deletion receipt throttle bounds')
        if self.MAIL_LIVE_ENABLED and (self.MAIL_PROVIDER != 'resend' or not self.RESEND_API_KEY or not self.MAIL_FROM):
            raise ConfigError('Live mail requires Resend credentials and sender')
        for value in (self.ANALYSIS_DAILY_LIMIT, self.CHAT_DAILY_LIMIT, self.UPLOAD_DAILY_LIMIT,
                      self.STORAGE_DAILY_BYTES, self.EXPORT_DAILY_LIMIT, self.SOURCE_STORAGE_LIMIT_BYTES,
                      self.MODEL_DAILY_COST_PAISE, self.MODEL_DAILY_TOKEN_LIMIT, self.GLOBAL_MODEL_DAILY_COST_PAISE):
            if type(value) is not int or not 0 <= value <= 10**13:
                raise ConfigError("Invalid resource limit")
        if not (60 <= self.RETENTION_INTERVAL_SECONDS <= 86400 and 30 <= self.WORKER_STALE_SECONDS <= 3600):
            raise ConfigError("Invalid operations scheduling bounds")
        if not (1 <= self.SOURCE_RETENTION_DAYS <= 3650 and 1 <= self.BACKUP_RETENTION_DAYS <= 3650
                and 1 <= self.EXPORT_TTL_SECONDS <= 3600 and 1 <= self.STATEMENT_MAX_BYTES <= 10*1024*1024
                and 1 <= self.STATEMENT_MAX_ROWS <= 10000 and 1 <= self.STATEMENT_TIMEOUT_SECONDS <= 30):
            raise ConfigError("Invalid retention or parser bounds")
        if self.is_production_like and self.SYNTHETIC_STATEMENTS_ENABLED:
            raise ConfigError("Synthetic statements cannot be enabled in production-like environments")
        weak = key.strip().lower() in _PLACEHOLDER_SECRETS or len(key) < MIN_SECRET_LENGTH
        if self.is_production_like:
            if weak:
                raise ConfigError(
                    "SECRET_KEY is missing, a known placeholder, or shorter than "
                    f"{MIN_SECRET_LENGTH} characters; refusing to start in APP_ENV={self.APP_ENV!r}."
                )
            if self.CORS_ORIGINS == ["*"]:
                raise ConfigError("CORS_ORIGINS must not be '*' in a production-like environment.")
            if self.DATABASE_URL.startswith("sqlite") and os.getenv("ALLOW_SQLITE_IN_PRODUCTION") != "1":
                raise ConfigError(
                    "SQLite is for local use only; set DATABASE_URL to PostgreSQL "
                    "(or ALLOW_SQLITE_IN_PRODUCTION=1 for a documented transitional deployment)."
                )
        elif weak:
            # Per-process ephemeral key: unguessable, never a shared constant.
            type(self).SECRET_KEY = secrets.token_urlsafe(48)
            type(self)._ephemeral_key = True

    _ephemeral_key = False


config = Config()
