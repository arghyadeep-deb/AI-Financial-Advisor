from sqlalchemy import (
    Column, Integer, String, Float,
    Boolean, DateTime, Text, ForeignKey, JSON
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime

Base = declarative_base()


class User(Base):
    __tablename__ = "users"

    id              = Column(Integer,  primary_key=True, index=True)
    email           = Column(String,   unique=True, index=True, nullable=False)
    full_name       = Column(String,   nullable=False)
    hashed_password = Column(String,   nullable=False)
    is_active       = Column(Boolean,  default=True)
    created_at      = Column(DateTime, default=datetime.utcnow)

    profile         = relationship("FinancialProfile", back_populates="user", uselist=False)
    financial_state = relationship("FinancialState",   back_populates="user", uselist=False)
    threads         = relationship("Thread",           back_populates="user")


class FinancialProfile(Base):
    __tablename__ = "financial_profiles"

    id                   = Column(Integer,  primary_key=True, index=True)
    user_id              = Column(Integer,  ForeignKey("users.id"), unique=True)
    age                  = Column(Integer)
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
    monthly_credit_spend = Column(Float,   default=0)
    top_spend_categories = Column(JSON)
    created_at           = Column(DateTime, default=datetime.utcnow)
    updated_at           = Column(DateTime, default=datetime.utcnow,
                                  onupdate=datetime.utcnow)

    user = relationship("User", back_populates="profile")


class FinancialState(Base):
    __tablename__ = "financial_state"

    id                   = Column(Integer,  primary_key=True, index=True)
    user_id              = Column(Integer,  ForeignKey("users.id"), unique=True)
    health_score         = Column(Float,    default=0)
    portfolio_value      = Column(Float,    default=0)
    monthly_savings_rate = Column(Float,    default=0)
    last_recommendations = Column(JSON)
    last_updated         = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="financial_state")


class Thread(Base):
    __tablename__ = "threads"

    id          = Column(Integer,  primary_key=True, index=True)
    user_id     = Column(Integer,  ForeignKey("users.id"))
    user_name   = Column(String,   nullable=True)
    user_email  = Column(String,   nullable=True)
    title       = Column(String)
    thread_type = Column(String)
    created_at  = Column(DateTime, default=datetime.utcnow)

    user     = relationship("User",    back_populates="threads")
    messages = relationship("Message", back_populates="thread")


class Message(Base):
    __tablename__ = "messages"

    id         = Column(Integer,  primary_key=True, index=True)
    thread_id  = Column(Integer,  ForeignKey("threads.id"))
    user_id    = Column(Integer,  ForeignKey("users.id"), nullable=True)
    user_name  = Column(String,   nullable=True)
    role       = Column(String)
    content    = Column(Text)
    extra_data = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)

    thread = relationship("Thread", back_populates="messages")