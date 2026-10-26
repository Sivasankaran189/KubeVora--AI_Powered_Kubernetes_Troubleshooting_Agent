from typing import List, Optional
from pydantic import BaseModel, Field


class ClusterSummary(BaseModel):
    id: str
    name: str
    provider: str
    region: str
    status: str
    is_local: bool = False
    node_count: int = 1


class ClusterStatus(BaseModel):
    name: str
    status: str
    k8s_version: str
    nodes_ready: int
    nodes_total: int
    total_pods: int
    healthy_pods: int
    warning_events: int
    active_investigations: int
    cpu_usage_pct: float
    memory_usage_pct: float
    provider: str = "kind / local docker"
    last_synced: str


class NamespaceInfo(BaseModel):
    name: str
    status: str
    pod_count: int
    healthy_pods: int
    warning_count: int
    is_system: bool = False


class WorkloadItem(BaseModel):
    id: str
    name: str
    namespace: str
    kind: str  # Deployment, Pod, StatefulSet, DaemonSet
    status: str  # Running, CrashLoopBackOff, ImagePullBackOff, Pending, Error
    ready_replicas: str
    restarts: int
    age: str
    cpu_usage: str
    memory_usage: str
    last_event: str
    message: Optional[str] = None


class ClusterEvent(BaseModel):
    id: str
    namespace: str
    type: str  # Warning, Normal, Error
    reason: str
    object: str
    message: str
    timestamp: str
    count: int
