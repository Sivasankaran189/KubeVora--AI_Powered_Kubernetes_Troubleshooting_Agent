from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class EvidenceItem(BaseModel):
    id: str
    type: str  # k8s_event, container_logs, metric_spike, exit_code, cgroup_event
    source: str  # kubelet, containerd, prometheus, apiserver
    timestamp: str
    description: str
    snippet: Optional[str] = None
    severity: str = "warning"  # info, warning, critical


class SafeFixPreview(BaseModel):
    remediation_type: str  # resource_limits_patch, rollback_image, fix_configmap, secret_mount
    description: str
    diff: str
    command: str
    risk_level: str  # low, medium, high
    rollback_plan: str
    verified_dry_run: bool = True


class InvestigationCreate(BaseModel):
    title: str = Field(..., min_length=3, description="Incident title or problem summary")
    namespace: str = Field(..., description="Target Kubernetes namespace")
    resource_kind: str = Field(..., description="Target resource kind: Pod, Deployment, StatefulSet")
    resource_name: str = Field(..., description="Name of the failing workload")
    symptom: str = Field(..., description="Observed symptom or alert trigger")
    severity: str = Field("warning", description="Severity: info, warning, critical")


class InvestigationSummary(BaseModel):
    id: str
    title: str
    namespace: str
    resource_kind: str
    resource_name: str
    status: str  # analyzing, root_cause_found, fix_ready, resolved
    severity: str
    root_cause: str
    confidence_pct: int
    fingerprint: str
    created_at: str
    updated_at: str
    evidence_count: int
    has_fix_preview: bool


class InvestigationDetail(InvestigationSummary):
    evidence: List[EvidenceItem] = Field(default_factory=list)
    fix_preview: Optional[SafeFixPreview] = None
    timeline: List[dict] = Field(default_factory=list)


# Prompt 4: Real PostgreSQL Persisted Investigation Schemas
class PersistedInvestigationSummary(BaseModel):
    id: str
    created_at: str
    cluster_context: str
    namespace: str
    status: str
    root_cause: Optional[str] = None
    confidence: int = 0
    confidence_level: str = "medium"
    duration_seconds: float = 0.0


class PersistedInvestigationDetail(PersistedInvestigationSummary):
    explanation: Optional[str] = None
    suggested_fix: Optional[str] = None
    kubectl_commands: Optional[List[dict]] = None
    yaml_proposal: Optional[str] = None
    prevention_recommendations: Optional[List[str]] = None
    evidence_gaps: Optional[List[str]] = None
    raw_evidence: Optional[dict] = None
    fingerprint_hash: Optional[str] = None
    completed_at: Optional[str] = None
    findings: List[dict] = Field(default_factory=list)
