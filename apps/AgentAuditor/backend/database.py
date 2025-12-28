"""
Database models and session management
"""
import os
from contextlib import contextmanager
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from typing import Generator
import logging

from backend.config import settings
from backend.base import Base  # Changed from backend.models

logger = logging.getLogger(__name__)

# Create database directory if needed
db_path = settings.database_url.replace("sqlite:///", "")
if db_path.startswith("./"):
    db_dir = os.path.dirname(db_path)
    if db_dir and not os.path.exists(db_dir):
        os.makedirs(db_dir, exist_ok=True)

# Create engine
engine = create_engine(
    settings.database_url,
    connect_args={"check_same_thread": False} if "sqlite" in settings.database_url else {},
    echo=False
)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db():
    """Initialize database tables"""
    try:
        # Import models to register them with Base
        from backend.models import Agent, Audit  # noqa
        
        Base.metadata.create_all(bind=engine)
        print("Database tables created successfully")
        logger.info("Database tables created successfully")
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        raise


def get_db_session() -> Generator[Session, None, None]:
    """
    FastAPI dependency for database sessions

    Usage:
        @app.get("/example")
        def example(db: Session = Depends(get_db_session)):
            ...
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@contextmanager
def get_db_context():
    """
    Context manager for manual database sessions

    Usage:
        with get_db_context() as db:
            ...
    """
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
