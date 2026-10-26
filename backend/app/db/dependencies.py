"""
FastAPI Database Session Dependency for KubeVora
"""
from typing import Generator
from sqlalchemy.orm import Session
from app.db.session import SessionLocal


def get_db() -> Generator[Session, None, None]:
    """Yield a database session and safely close it after request completion."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
