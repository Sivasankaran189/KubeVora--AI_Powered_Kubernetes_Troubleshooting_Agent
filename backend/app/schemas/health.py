from typing import List
from pydantic import BaseModel, Field


class ServiceHealth(BaseModel):
    name: str = Field(..., description="Subsystem or service name")
    status: str = Field(..., description="Service status: healthy, degraded, or unhealthy")
    message: str = Field(..., description="Detailed probe message")
    latency_ms: float = Field(..., description="Ping/query latency in milliseconds")


class HealthStatus(BaseModel):
    status: str = Field(..., description="Overall system health status")
    timestamp: str = Field(..., description="ISO 8601 UTC timestamp")
    version: str = Field(..., description="Application version")
    environment: str = Field(..., description="Active runtime environment")
    services: List[ServiceHealth] = Field(default_factory=list, description="Subsystem probe breakdown")


class ProbeStatus(BaseModel):
    status: str
    timestamp: str
    service: str = "kubevora-backend"
