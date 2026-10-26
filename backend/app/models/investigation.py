"""
SQLAlchemy Model: Investigation
"""
import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Integer, Float, Text, JSON, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.db.base import Base


class Investigation(Base):
    __tablename__ = "investigations"

    id = Column(String, primary_key=True, default=lambda: f"inv_{uuid.uuid4().hex[:12]}")
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    cluster_context = Column(String(100), default="default")
    namespace = Column(String(100), default="default", index=True)
    status = Column(String(50), default="running", index=True)  # running, completed, partially_completed, failed
    
    # Diagnosis Details
    root_cause = Column(Text, nullable=True)
    explanation = Column(Text, nullable=True)
    confidence = Column(Integer, default=0)
    confidence_level = Column(String(20), default="medium")  # low, medium, high
    suggested_fix = Column(Text, nullable=True)
    kubectl_commands = Column(JSON, nullable=True)  # List of {"command", "purpose", "risk"}
    yaml_proposal = Column(Text, nullable=True)
    prevention_recommendations = Column(JSON, nullable=True)
    evidence_gaps = Column(JSON, nullable=True)
    
    # Telemetry and metadata
    raw_evidence = Column(JSON, nullable=True)  # Summary of collected logs/events/pods
    duration_seconds = Column(Float, default=0.0)
    fingerprint_hash = Column(String(64), nullable=True, index=True)
    error_summary = Column(Text, nullable=True)

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), index=True)
    completed_at = Column(DateTime, nullable=True)

    # Relationships
    user = relationship("User", back_populates="investigations")
    findings = relationship("Finding", back_populates="investigation", cascade="all, delete-orphan")
