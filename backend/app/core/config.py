from typing import List, Optional, Union
from pydantic import AnyHttpUrl, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"
    )

    PROJECT_NAME: str = "KubeVora"
    TAGLINE: str = "Unified System Intelligence & Autonomous Resolution Platform"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"
    ENVIRONMENT: str = "development"

    # Security & JWT
    SECRET_KEY: str = "kubevora-super-secret-key-change-in-production-2026-sre-agent"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24 hours

    # CORS
    BACKEND_CORS_ORIGINS: List[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
        "http://localhost:13001",
        "http://127.0.0.1:13001",
        "http://localhost:18000",
        "http://127.0.0.1:18000",
    ]

    # System Environment Settings
    CLUSTER_NAME: str = "production-grid-primary"
    K8S_VERSION: str = "2026.4 Standard"

    # Kubernetes Investigation Engine
    KUBECONFIG_PATH: Optional[str] = None
    KUBERNETES_CONTEXT: Optional[str] = None
    KUBEVORA_DEFAULT_NAMESPACE: str = "default"
    KUBEVORA_COMMAND_TIMEOUT: int = 15
    KUBEVORA_LOG_TAIL: int = 100
    KUBEVORA_STUCK_THRESHOLD_SECONDS: int = 300

    # AI Reasoning (Gemini API)
    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-1.5-pro"
    GEMINI_TIMEOUT_SECONDS: int = 30
    GEMINI_MAX_RETRIES: int = 2

    # Persistence (Placeholder for Phase 2)
    DATABASE_URL: str = "sqlite:///./kubevora.db"


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
