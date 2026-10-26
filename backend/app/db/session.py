"""
SQLAlchemy Engine & Session Factory for KubeVora
"""
from typing import Generator
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from app.core.config import settings
from app.db.base import Base

db_url = settings.DATABASE_URL
connect_args = {}

if "sqlite" in db_url:
    connect_args = {"check_same_thread": False}

engine = create_engine(
    db_url,
    connect_args=connect_args,
    pool_pre_ping=True if "sqlite" not in db_url else False,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db(custom_engine=None):
    """Create all tables if they do not exist."""
    target_engine = custom_engine or engine
    Base.metadata.create_all(bind=target_engine)
