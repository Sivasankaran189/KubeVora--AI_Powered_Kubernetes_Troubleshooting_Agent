"""
SQLAlchemy Model: Finding
"""
import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Text, JSON, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.db.base import Base


class Finding(Base):
    __tablename__ = "findings"

    id = Column(String, primary_key=True, default=lambda: f"fnd_{uuid.uuid4().hex[:12]}")
    investigation_id = Column(String, ForeignKey("investigations.id", ondelete="CASCADE"), nullable=False, index=True)
    category = Column(String(50), nullable=False, index=True)  # pod, log, event, deployment, network
    resource_kind = Column(String(50), nullable=True)  # Pod, Deployment, Service
    resource_name = Column(String(255), nullable=True)
    namespace = Column(String(100), default="default")
    severity = Column(String(20), default="warning")  # critical, warning, info
    summary = Column(Text, nullable=False)
    evidence_detail = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    # Relationships
    investigation = relationship("Investigation", back_populates="findings")
