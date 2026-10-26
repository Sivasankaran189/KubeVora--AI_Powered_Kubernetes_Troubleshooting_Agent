"""
SQLAlchemy Model: IncidentFingerprint
Tracks deterministic failure signatures to identify recurring Kubernetes incidents.
"""
import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Integer, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.db.base import Base


class IncidentFingerprint(Base):
    __tablename__ = "incident_fingerprints"

    id = Column(String, primary_key=True, default=lambda: f"fp_{uuid.uuid4().hex[:12]}")
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True)
    fingerprint_hash = Column(String(64), unique=True, index=True, nullable=False)
    failure_category = Column(String(100), nullable=False)
    resource_kind = Column(String(50), nullable=True)
    resource_name = Column(String(255), nullable=True)
    namespace = Column(String(100), default="default", index=True)
    first_observed_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    last_observed_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    occurrence_count = Column(Integer, default=1)
    last_investigation_id = Column(String(64), nullable=True)

    # Relationships
    user = relationship("User", back_populates="fingerprints")
