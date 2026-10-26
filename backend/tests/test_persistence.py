"""
Unit & Integration Tests for PostgreSQL & SQLAlchemy Persistence Layer (Prompt 4).
Runs with an isolated test SQLite in-memory / temporary engine, guaranteeing tests run offline and fast.
"""
import json
import pytest
from datetime import datetime, timezone
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.base import Base
from app.models.user import User
from app.models.investigation import Investigation
from app.models.finding import Finding
from app.models.fingerprint import IncidentFingerprint
from app.services.persistence_service import persistence_service
from app.services.user_store import UserStore
from app.schemas.auth import UserCreate, UserLogin


# ---------------------------------------------------------------------------
# Test Database Fixture
# ---------------------------------------------------------------------------

@pytest.fixture
def db_session():
    """Create an isolated in-memory SQLite database session for testing."""
    test_engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=test_engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


# ---------------------------------------------------------------------------
# 1. User Registration & Authentication Tests
# ---------------------------------------------------------------------------

def test_user_registration_and_argon2(db_session):
    store = UserStore()
    user_in = UserCreate(
        username="devops_sam",
        email="sam@kubevora.dev",
        password="securePassword123!",
        full_name="Sam DevOps",
        role="Senior SRE"
    )

    created = store.create_user(user_in, db=db_session)
    assert created.username == "devops_sam"
    assert created.email == "sam@kubevora.dev"

    # Verify user exists in database and password is not plaintext
    db_user = db_session.query(User).filter(User.username == "devops_sam").first()
    assert db_user is not None
    assert db_user.hashed_password != "securePassword123!"
    assert "$argon2" in db_user.hashed_password


def test_duplicate_user_rejection(db_session):
    store = UserStore()
    user_in = UserCreate(
        username="unique_user",
        email="unique@kubevora.dev",
        password="password123",
    )
    store.create_user(user_in, db=db_session)

    # Attempt duplicate username
    with pytest.raises(ValueError, match="already registered"):
        store.create_user(user_in, db=db_session)


def test_user_authentication_success_and_failure(db_session):
    store = UserStore()
    user_in = UserCreate(
        username="auth_tester",
        email="auth@kubevora.dev",
        password="correctPassword123",
    )
    store.create_user(user_in, db=db_session)

    # Success
    auth_user = store.authenticate_user("auth_tester", "correctPassword123", db=db_session)
    assert auth_user is not None
    assert auth_user.username == "auth_tester"

    # Also authenticate via email
    auth_email = store.authenticate_user("auth@kubevora.dev", "correctPassword123", db=db_session)
    assert auth_email is not None

    # Failure: wrong password
    bad_pw = store.authenticate_user("auth_tester", "wrongPassword", db=db_session)
    assert bad_pw is None

    # Failure: non-existent user
    non_existent = store.authenticate_user("ghost_user", "pass", db=db_session)
    assert non_existent is None


# ---------------------------------------------------------------------------
# 2. Investigation Persistence & Findings Tests
# ---------------------------------------------------------------------------

def test_investigation_lifecycle_persistence(db_session):
    store = UserStore()
    user = store.create_user(
        UserCreate(username="sre_inv", email="inv@kubevora.dev", password="password123"),
        db=db_session
    )

    # 1. Create running investigation
    inv = persistence_service.create_investigation(
        db=db_session,
        user_id=user.id,
        cluster_context="kind-kubevora",
        namespace="default"
    )
    assert inv.status == "running"
    assert inv.user_id == user.id

    # 2. Record findings
    evidence = {
        "pods": {
            "problematic_pods": [
                {
                    "name": "payment-service",
                    "namespace": "default",
                    "status": "CrashLoopBackOff",
                    "message": "CrashLoopBackOff restarting"
                }
            ]
        },
        "logs": {
            "collected_logs": [
                {
                    "pod": "payment-service",
                    "error_detected": True,
                    "relevant_lines": ["FATAL: DATABASE_URL missing"]
                }
            ]
        },
        "deployments": {"deployments": []},
        "network": {"services": []}
    }

    findings = persistence_service.record_findings(db_session, inv.id, evidence)
    assert len(findings) == 2
    assert findings[0].category == "pod"
    assert findings[1].category == "log"

    # 3. Finalize investigation with diagnosis
    diagnosis = {
        "root_cause": "DATABASE_URL missing from deployment spec",
        "explanation": "Container cannot connect without database credentials.",
        "confidence": 94,
        "confidence_level": "high",
        "suggested_fix": "Add DATABASE_URL environment variable to deployment spec.",
        "kubectl_commands": [{"command": "kubectl describe deployment payment-service", "purpose": "Check env", "risk": "read-only"}],
        "yaml_proposal": "env:\n  - name: DATABASE_URL\n    value: postgres://...",
        "prevention_recommendations": ["Validate config on startup"],
        "evidence_gaps": []
    }

    finalized = persistence_service.finalize_investigation(
        db=db_session,
        investigation_id=inv.id,
        evidence=evidence,
        diagnosis=diagnosis,
        duration_seconds=2.45,
        status="completed"
    )

    assert finalized.status == "completed"
    assert finalized.confidence == 94
    assert finalized.root_cause == diagnosis["root_cause"]
    assert finalized.duration_seconds == 2.45


# ---------------------------------------------------------------------------
# 3. Incident Fingerprinting & Recurrence Tests
# ---------------------------------------------------------------------------

def test_incident_fingerprint_generation_and_recurrence(db_session):
    store = UserStore()
    user = store.create_user(UserCreate(username="fp_user", email="fp@kubevora.dev", password="password123"), db=db_session)

    inv1 = persistence_service.create_investigation(db_session, user.id, "kind-kubevora", "production")

    evidence = {
        "pods": {
            "problematic_pods": [
                {
                    "name": "checkout-api-7b89f64c-xz92a",
                    "status": "CrashLoopBackOff",
                    "message": "Connection refused to redis:6379"
                }
            ]
        },
        "logs": {
            "collected_logs": [{"relevant_lines": ["Connection refused to redis:6379"]}]
        }
    }

    # First occurrence
    fp1 = persistence_service.record_or_update_fingerprint(
        db=db_session,
        user_id=user.id,
        namespace="production",
        evidence=evidence,
        diagnosis={},
        investigation_id=inv1.id
    )
    assert fp1 is not None

    record1 = db_session.query(IncidentFingerprint).filter(IncidentFingerprint.fingerprint_hash == fp1).first()
    assert record1.occurrence_count == 1

    # Second occurrence (recurring failure with different pod hash suffix)
    inv2 = persistence_service.create_investigation(db_session, user.id, "kind-kubevora", "production")
    evidence_recurring = {
        "pods": {
            "problematic_pods": [
                {
                    "name": "checkout-api-89f1d04b-qp11z",  # Pod restarted with new replica hash
                    "status": "CrashLoopBackOff",
                    "message": "Connection refused to redis:6379"
                }
            ]
        },
        "logs": {
            "collected_logs": [{"relevant_lines": ["Connection refused to redis:6379"]}]
        }
    }

    fp2 = persistence_service.record_or_update_fingerprint(
        db=db_session,
        user_id=user.id,
        namespace="production",
        evidence=evidence_recurring,
        diagnosis={},
        investigation_id=inv2.id
    )

    # Must match the same fingerprint!
    assert fp1 == fp2

    record2 = db_session.query(IncidentFingerprint).filter(IncidentFingerprint.fingerprint_hash == fp2).first()
    assert record2.occurrence_count == 2
    assert record2.last_investigation_id == inv2.id


# ---------------------------------------------------------------------------
# 4. User Isolation Security Tests (404 on Unauthorized Access)
# ---------------------------------------------------------------------------

def test_user_investigation_isolation(db_session):
    store = UserStore()
    user_a = store.create_user(UserCreate(username="user_alice", email="alice@test.dev", password="password123"), db=db_session)
    user_b = store.create_user(UserCreate(username="user_bob", email="bob@test.dev", password="password123"), db=db_session)

    # Alice creates an investigation
    alice_inv = persistence_service.create_investigation(db_session, user_a.id, "default", "production")

    # Alice can retrieve her own investigation
    found_alice = persistence_service.get_user_investigation(db_session, user_id=user_a.id, investigation_id=alice_inv.id)
    assert found_alice is not None
    assert found_alice.id == alice_inv.id

    # Bob CANNOT retrieve Alice's investigation (returns None -> 404 in API)
    found_bob = persistence_service.get_user_investigation(db_session, user_id=user_b.id, investigation_id=alice_inv.id)
    assert found_bob is None

    # Bob's history list does not contain Alice's investigation
    bobs_history = persistence_service.list_user_investigations(db_session, user_id=user_b.id)
    assert len(bobs_history) == 0
