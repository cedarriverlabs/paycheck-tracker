"""
Database models and connection for Paycheck Tracker.
Uses SQLAlchemy. Defaults to SQLite for local/dev.
For production, set DATABASE_URL to a Postgres connection string (Neon, Supabase, etc.).
"""

import os
from datetime import date, datetime
from typing import Optional, List

from sqlalchemy import (
    create_engine, Column, Integer, String, Float, Date, DateTime,
    Boolean, ForeignKey, Text, Enum as SQLEnum
)
from sqlalchemy.orm import declarative_base, sessionmaker, relationship
from sqlalchemy.pool import StaticPool
import enum

Base = declarative_base()

# ---------- Enums ----------
class CategoryType(str, enum.Enum):
    INCOME = "Income"
    SAVINGS = "Savings"
    BILLS = "Bills"
    EXPENSES = "Expenses"
    DEBT = "Debt"


# ---------- Models ----------
class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    username = Column(String(80), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    email = Column(String(255), nullable=True)  # for notifications
    created_at = Column(DateTime, default=datetime.utcnow)


class PaycheckPeriod(Base):
    __tablename__ = "paycheck_periods"

    id = Column(Integer, primary_key=True)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    label = Column(String(50))  # e.g. "Aug 14 – Aug 27"
    is_current = Column(Boolean, default=False)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    transactions = relationship("Transaction", back_populates="period", cascade="all, delete-orphan")


class Subcategory(Base):
    """Master list of categories + subcategories with optional recurring info."""
    __tablename__ = "subcategories"

    id = Column(Integer, primary_key=True)
    category = Column(String(50), nullable=False)  # Income / Savings / Bills / Expenses / Debt
    name = Column(String(100), nullable=False)
    is_recurring = Column(Boolean, default=False)
    typical_amount = Column(Float, nullable=True)
    due_info = Column(String(50), nullable=True)  # e.g. "1st (AP)", "MT", "23rd (BP)"
    notes = Column(Text, nullable=True)
    active = Column(Boolean, default=True)

    __table_args__ = (
        # unique constraint on category + name
    )


class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True)
    period_id = Column(Integer, ForeignKey("paycheck_periods.id"), nullable=False)
    date = Column(Date, nullable=False)
    amount = Column(Float, nullable=False)
    category = Column(String(50), nullable=False)
    subcategory = Column(String(100), nullable=False)
    description = Column(String(255), nullable=True)
    is_suggested = Column(Boolean, default=False)  # came from recurring pre-load
    payment_method = Column(String(50), nullable=True)  # Credit Card, Auto-pay, Manual, etc.
    created_at = Column(DateTime, default=datetime.utcnow)

    period = relationship("PaycheckPeriod", back_populates="transactions")


# ---------- Engine & Session ----------
def get_database_url() -> str:
    url = os.getenv("DATABASE_URL")
    if url:
        # Render / Neon / Supabase sometimes give postgres:// instead of postgresql://
        if url.startswith("postgres://"):
            url = url.replace("postgres://", "postgresql://", 1)
        return url
    # Default: local SQLite (or ephemeral on Streamlit Cloud until Postgres is connected)
    return "sqlite:////tmp/paycheck.db"


def get_engine():
    url = get_database_url()
    if url.startswith("sqlite"):
        return create_engine(
            url,
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
    return create_engine(url)


engine = get_engine()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db():
    """Create all tables."""
    Base.metadata.create_all(bind=engine)


def get_session():
    return SessionLocal()
