from datetime import datetime, timezone

from sqlalchemy import (
    BigInteger, Boolean, Column, DateTime, Float, ForeignKey, Index, Integer,
    JSON, String, Text, UniqueConstraint, text,
)
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


def utcnow() -> datetime:
    """Naive UTC timestamp (column type is DateTime without timezone)."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


class User(Base):
    __tablename__ = "users"

    id              = Column(Integer,  primary_key=True, index=True)
    email           = Column(String,   unique=True, index=True, nullable=False)
    full_name       = Column(String,   nullable=False)
    # Argon2id PHC string for scheme "argon2id"; hex HMAC digest for the
    # legacy scheme, which is rehashed on first successful login.
    hashed_password = Column(String,   nullable=False)
    password_scheme = Column(String,   nullable=False, default="argon2id",
                             server_default="legacy_hmac_sha256")
    password_changed_at = Column(DateTime, nullable=True)
    is_active       = Column(Boolean,  default=True)
    created_at      = Column(DateTime, default=utcnow)

    profile         = relationship("FinancialProfile", back_populates="user", uselist=False)
    financial_state = relationship("FinancialState",   back_populates="user", uselist=False)
    threads         = relationship("Thread",           back_populates="user")


class AuthSession(Base):
    """Server-side session record so tokens can be revoked (F001-FR09)."""
    __tablename__ = "auth_sessions"

    id             = Column(String(36), primary_key=True)          # embedded as `sid` claim
    user_id        = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    created_at     = Column(DateTime, default=utcnow, nullable=False)
    expires_at     = Column(DateTime, nullable=False)
    revoked_at     = Column(DateTime, nullable=True)
    revoked_reason = Column(String(40), nullable=True)


class PasswordResetToken(Base):
    """Single-use recovery token.  Only a SHA-256 digest is stored."""
    __tablename__ = "password_reset_tokens"

    id         = Column(Integer, primary_key=True)
    user_id    = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    token_hash = Column(String(64), nullable=False, unique=True)
    created_at = Column(DateTime, default=utcnow, nullable=False)
    expires_at = Column(DateTime, nullable=False)
    used_at    = Column(DateTime, nullable=True)


class LoginThrottle(Base):
    """Failed-login counters keyed by a digest of the normalised email.

    Unknown emails are tracked identically so responses and timing do not
    reveal whether an account exists.
    """
    __tablename__ = "login_throttle"

    key          = Column(String(64), primary_key=True)
    failures     = Column(Integer, nullable=False, default=0)
    window_start = Column(DateTime, nullable=False, default=utcnow)
    locked_until = Column(DateTime, nullable=True)


class FinancialProfile(Base):
    __tablename__ = "financial_profiles"

    id                   = Column(Integer,  primary_key=True, index=True)
    user_id              = Column(Integer,  ForeignKey("users.id"), unique=True)
    age                  = Column(Integer)
    # Legacy float columns are kept for rollback compatibility and are written
    # ONLY by ProfileService, derived from the *_paise columns below.
    monthly_income       = Column(Float)
    monthly_expenses     = Column(Float)
    existing_savings     = Column(Float,   default=0)
    existing_investments = Column(Float,   default=0)
    existing_debts       = Column(Float,   default=0)
    risk_tolerance       = Column(String)
    investment_horizon   = Column(String)
    financial_goals      = Column(JSON)
    employment_type      = Column(String)
    credit_score         = Column(Integer)
    credit_score_source  = Column(String(24), nullable=True)   # user | legacy_unverified
    monthly_credit_spend = Column(Float,   default=0)
    top_spend_categories = Column(JSON)

    # Canonical exact money (integer paise).  Nullable only for rows that have
    # not yet been migrated; ProfileService treats NULL as "unknown".
    monthly_income_paise        = Column(BigInteger, nullable=True)
    monthly_expenses_paise      = Column(BigInteger, nullable=True)
    existing_savings_paise      = Column(BigInteger, nullable=True)
    existing_investments_paise  = Column(BigInteger, nullable=True)
    existing_debts_paise        = Column(BigInteger, nullable=True)     # debt BALANCE
    monthly_debt_payment_paise  = Column(BigInteger, nullable=True)     # distinct from balance; NULL = not declared
    monthly_credit_spend_paise  = Column(BigInteger, nullable=True)

    revision       = Column(Integer, nullable=False, default=1, server_default="1")
    schema_version = Column(Integer, nullable=False, default=1, server_default="1")
    created_at     = Column(DateTime, default=utcnow)
    updated_at     = Column(DateTime, default=utcnow, onupdate=utcnow)

    user = relationship("User", back_populates="profile")


class ProfileRevision(Base):
    """Immutable copy of the profile inputs at each revision."""
    __tablename__ = "profile_revisions"
    __table_args__ = (UniqueConstraint("user_id", "revision", name="uq_profile_revision"),)

    id         = Column(Integer, primary_key=True)
    user_id    = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    revision   = Column(Integer, nullable=False)
    snapshot   = Column(JSON, nullable=False)       # paise ints + enums, no floats
    source     = Column(String(24), nullable=False, default="user_edit")
    created_at = Column(DateTime, default=utcnow, nullable=False)


class FinancialState(Base):
    __tablename__ = "financial_state"

    id                   = Column(Integer,  primary_key=True, index=True)
    user_id              = Column(Integer,  ForeignKey("users.id"), unique=True)
    health_score         = Column(Float,    default=0)
    # Legacy: held a *projected* corpus.  Never populated with projections any
    # more; observed holdings are only what the user declared (see FR-004).
    portfolio_value      = Column(Float,    default=0)
    monthly_savings_rate = Column(Float,    default=0)
    last_recommendations = Column(JSON)             # legacy cache, no longer read
    last_updated         = Column(DateTime, default=utcnow)
    # Additive (FR-002 / FR-004)
    health_score_known         = Column(Boolean, nullable=True)
    health_score_revision      = Column(Integer, nullable=True)

    user = relationship("User", back_populates="financial_state")


class Analysis(Base):
    """One analysis run: owner, kind, status, input revision, provenance."""
    __tablename__ = "analyses"
    __table_args__ = (Index("ix_analyses_user_kind_completed", "user_id", "kind", "completed_at"),)

    id               = Column(String(36), primary_key=True)
    user_id          = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    kind             = Column(String(24), nullable=False)
    # running | complete | degraded | partial | failed | superseded
    status           = Column(String(16), nullable=False)
    profile_revision = Column(Integer, nullable=False)
    rule_version     = Column(String(24), nullable=False)
    is_scenario      = Column(Boolean, nullable=False, default=False, server_default="0")
    started_at       = Column(DateTime, default=utcnow, nullable=False)
    completed_at     = Column(DateTime, nullable=True)
    snapshot         = Column(JSON)                 # canonical finance snapshot used
    results          = Column(JSON)
    errors           = Column(JSON)
    section_status   = Column(JSON)                 # per-section provenance (llm | fallback | deterministic)


class Thread(Base):
    __tablename__ = "threads"

    id          = Column(Integer,  primary_key=True, index=True)
    user_id     = Column(Integer,  ForeignKey("users.id"))
    user_name   = Column(String,   nullable=True)
    user_email  = Column(String,   nullable=True)
    title       = Column(String)
    thread_type = Column(String)
    created_at  = Column(DateTime, default=utcnow)

    user     = relationship("User",    back_populates="threads")
    messages = relationship("Message", back_populates="thread")


class Message(Base):
    __tablename__ = "messages"
    __table_args__ = (
        # One logical user turn per client-supplied id within a thread (FR-007).
        UniqueConstraint("thread_id", "client_message_id", "role", name="uq_message_client_id"),
        # ...and one user message per owner + client id across threads (retried first message; migration 0003).
        Index("uq_messages_owner_client_id", "user_id", "client_message_id", unique=True,
              sqlite_where=text("role = 'user' AND client_message_id IS NOT NULL"),
              postgresql_where=text("role = 'user' AND client_message_id IS NOT NULL")),
    )

    id         = Column(Integer,  primary_key=True, index=True)
    thread_id  = Column(Integer,  ForeignKey("threads.id"))
    user_id    = Column(Integer,  ForeignKey("users.id"), nullable=True)
    user_name  = Column(String,   nullable=True)
    role       = Column(String)
    content    = Column(Text)
    extra_data = Column(JSON)
    client_message_id = Column(String(64), nullable=True)
    created_at = Column(DateTime, default=utcnow)

    thread = relationship("Thread", back_populates="messages")

class ConsentRecord(Base):
    """Append-only choices; latest id is authoritative, including withdrawal."""
    __tablename__ = "consent_records"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    purpose = Column(String(40), nullable=False)
    granted = Column(Boolean, nullable=False)
    notice_version = Column(String(40), nullable=False)
    created_at = Column(DateTime, nullable=False, default=utcnow)

class WorkItem(Base):
    """Transactional outbox and leased work in one row; metadata only."""
    __tablename__ = "work_items"
    __table_args__ = (UniqueConstraint("user_id", "event_key", name="uq_work_owner_event"),)
    id = Column(String(36), primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    event_key = Column(String(100), nullable=False)
    kind = Column(String(40), nullable=False)
    consent_purpose = Column(String(40), nullable=True)
    state = Column(String(20), nullable=False, default="queued")
    fence = Column(Integer, nullable=False, default=0)
    attempts = Column(Integer, nullable=False, default=0)
    available_at = Column(DateTime, nullable=False, default=utcnow)
    lease_until = Column(DateTime, nullable=True)
    created_at = Column(DateTime, nullable=False, default=utcnow)

class NotificationPreference(Base):
    __tablename__ = "notification_preferences"
    user_id = Column(Integer, ForeignKey("users.id"), primary_key=True)
    enabled = Column(Boolean, nullable=False, default=True)
    categories = Column(JSON, nullable=False, default=lambda: ["report_ready", "reminder"])
    quiet_start = Column(Integer, nullable=True)
    quiet_end = Column(Integer, nullable=True)

class DeliveryAttempt(Base):
    __tablename__ = "delivery_attempts"
    __table_args__ = (UniqueConstraint("user_id", "event_key", name="uq_delivery_owner_event"),)
    id = Column(String(36), primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    event_key = Column(String(100), nullable=False)
    category = Column(String(40), nullable=False)
    state = Column(String(20), nullable=False)
    created_at = Column(DateTime, nullable=False, default=utcnow)

class QuotaUsage(Base):
    __tablename__ = "quota_usage"
    __table_args__ = (UniqueConstraint("user_id", "resource", "period", name="uq_quota_bucket"),)
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    resource = Column(String(40), nullable=False)
    period = Column(String(10), nullable=False)
    used = Column(BigInteger, nullable=False, default=0)
