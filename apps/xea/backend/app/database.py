"""
Database configuration and models for Xea.
Uses SQLite for development, easily switchable to PostgreSQL for production.
"""

import os
from datetime import datetime
from typing import Optional
from sqlalchemy import create_engine, Column, String, Integer, DateTime, Text, Float
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# Database URL - defaults to SQLite, can be overridden with DATABASE_URL env var
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./xea_history.db")

# Handle PostgreSQL URL format from some providers
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

# Create engine
if DATABASE_URL.startswith("sqlite"):
    engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
else:
    engine = create_engine(DATABASE_URL)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class ValidationHistory(Base):
    """Model for storing validation history."""
    __tablename__ = "validation_history"

    id = Column(Integer, primary_key=True, index=True)
    job_id = Column(String(64), unique=True, index=True, nullable=False)
    proposal_id = Column(String(64), index=True, nullable=True)  # For versioning
    version_number = Column(Integer, default=1)  # v1, v2, v3...
    proposal_hash = Column(String(64), index=True, nullable=False)
    proposal_title = Column(String(500), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    completed_at = Column(DateTime, nullable=True)
    status = Column(String(20), default="pending", nullable=False)
    claims_count = Column(Integer, default=0)
    overall_verdict = Column(String(20), nullable=True)
    confidence_score = Column(Float, nullable=True)
    ipfs_cid = Column(String(100), nullable=True)
    network_used = Column(String(50), nullable=True)
    evidence_json = Column(Text, nullable=True)  # Store evidence bundle as JSON


def init_db():
    """Initialize database tables."""
    Base.metadata.create_all(bind=engine)


def get_db():
    """Get database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# Initialize database on module import
init_db()
