import threading
import uuid
from datetime import datetime, timezone
from typing import Dict, Optional, Tuple
from sqlalchemy.orm import Session
from loguru import logger

from app.core.security import hash_password, verify_password
from app.schemas.auth import UserCreate, UserResponse
from app.models.user import User


class UserStore:
    def __init__(self):
        self._lock = threading.Lock()
        # id -> (UserResponse, hashed_password)
        self._users_by_id: Dict[str, Tuple[UserResponse, str]] = {}
        # username -> id
        self._by_username: Dict[str, str] = {}
        # email -> id
        self._by_email: Dict[str, str] = {}

        # Seed default admin SRE user in memory
        self._seed_default_user()

    def _seed_default_user(self):
        admin_id = "usr_sre_001"
        admin_pw_hash = hash_password("adminpassword123")
        admin_user = UserResponse(
            id=admin_id,
            username="admin_sre",
            email="admin@kube_vora.internal",
            full_name="Alex Vance (Lead SRE)",
            role="Cluster Administrator & SRE Lead",
            permissions=[
                "cluster:read",
                "cluster:write",
                "investigate:create",
                "investigate:execute_fix",
                "audit:read"
            ],
            created_at=datetime.now(timezone.utc).isoformat()
        )
        self._users_by_id[admin_id] = (admin_user, admin_pw_hash)
        self._by_username["admin_sre"] = admin_id
        self._by_email["admin@kube_vora.internal"] = admin_id

    def ensure_seeded_in_db(self, db: Session):
        """Seed admin user in DB if database is empty."""
        try:
            existing = db.query(User).filter(User.username == "admin_sre").first()
            if not existing:
                admin_pw_hash = hash_password("adminpassword123")
                db_user = User(
                    id="usr_sre_001",
                    username="admin_sre",
                    email="admin@kube_vora.internal",
                    hashed_password=admin_pw_hash,
                    full_name="Alex Vance (Lead SRE)",
                    role="Cluster Administrator & SRE Lead",
                    is_active=True,
                )
                db.add(db_user)
                db.commit()
        except Exception as e:
            logger.debug(f"DB user seed note: {e}")

    def create_user(self, user_in: UserCreate, db: Optional[Session] = None) -> UserResponse:
        with self._lock:
            # Check DB if session available
            if db:
                existing = db.query(User).filter(
                    (User.username == user_in.username.lower()) | (User.email == user_in.email.lower())
                ).first()
                if existing:
                    if existing.username == user_in.username.lower():
                        raise ValueError("Username already registered")
                    raise ValueError("Email address already registered")

            if user_in.username.lower() in self._by_username:
                raise ValueError("Username already registered")
            if user_in.email.lower() in self._by_email:
                raise ValueError("Email address already registered")

            user_id = f"usr_{uuid.uuid4().hex[:8]}"
            pw_hash = hash_password(user_in.password)
            user_response = UserResponse(
                id=user_id,
                username=user_in.username,
                email=user_in.email.lower(),
                full_name=user_in.full_name or user_in.username.title(),
                role=user_in.role or "Site Reliability Engineer",
                permissions=[
                    "cluster:read",
                    "investigate:create",
                    "investigate:view"
                ],
                created_at=datetime.now(timezone.utc).isoformat()
            )

            if db:
                db_user = User(
                    id=user_id,
                    username=user_in.username.lower(),
                    email=user_in.email.lower(),
                    hashed_password=pw_hash,
                    full_name=user_response.full_name,
                    role=user_response.role,
                    is_active=True,
                )
                db.add(db_user)
                db.commit()

            self._users_by_id[user_id] = (user_response, pw_hash)
            self._by_username[user_in.username.lower()] = user_id
            self._by_email[user_in.email.lower()] = user_id
            return user_response

    def get_by_id(self, user_id: str, db: Optional[Session] = None) -> Optional[UserResponse]:
        if db:
            db_user = db.query(User).filter(User.id == user_id).first()
            if db_user:
                return UserResponse(
                    id=db_user.id,
                    username=db_user.username,
                    email=db_user.email,
                    full_name=db_user.full_name,
                    role=db_user.role,
                    permissions=["cluster:read", "investigate:create", "investigate:view"],
                    created_at=db_user.created_at.isoformat() if db_user.created_at else datetime.now(timezone.utc).isoformat(),
                )

        with self._lock:
            record = self._users_by_id.get(user_id)
            return record[0] if record else None

    def get_by_username_or_email(self, identifier: str, db: Optional[Session] = None) -> Optional[Tuple[UserResponse, str]]:
        clean_id = identifier.strip().lower()
        if db:
            self.ensure_seeded_in_db(db)
            db_user = db.query(User).filter((User.username == clean_id) | (User.email == clean_id)).first()
            if db_user:
                resp = UserResponse(
                    id=db_user.id,
                    username=db_user.username,
                    email=db_user.email,
                    full_name=db_user.full_name,
                    role=db_user.role,
                    permissions=["cluster:read", "investigate:create", "investigate:view"],
                    created_at=db_user.created_at.isoformat() if db_user.created_at else datetime.now(timezone.utc).isoformat(),
                )
                return (resp, db_user.hashed_password)

        with self._lock:
            user_id = self._by_username.get(clean_id) or self._by_email.get(clean_id)
            if not user_id:
                return None
            return self._users_by_id.get(user_id)

    def authenticate_user(self, username_or_email: str, password: str, db: Optional[Session] = None) -> Optional[UserResponse]:
        record = self.get_by_username_or_email(username_or_email, db=db)
        if not record:
            return None
        user, hashed_password = record
        if verify_password(password, hashed_password):
            return user
        return None


# Global singleton store
user_store = UserStore()
