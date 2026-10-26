"""
KubeVora - Diagnosis Schemas
Pydantic schemas for structured AI SRE root-cause analysis and remediation.
"""
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class SupportingEvidenceItem(BaseModel):
    source: str = Field(..., description="Evidence source: pods, logs, events, deployments, network")
    resource: str = Field(..., description="Involved resource name (e.g., payment-service)")
    detail: str = Field(..., description="Specific collected log line, event message, or pod state")


class KubectlCommandProposal(BaseModel):
    command: str = Field(..., description="Actionable kubectl command")
    purpose: str = Field(..., description="Explanation of what the command does")
    risk: str = Field("read-only", description="Risk level: read-only, mutating, disruptive")


class DiagnosisResponse(BaseModel):
    root_cause: str = Field(..., description="Primary root-cause summary")
    explanation: str = Field(..., description="Detailed SRE explanation distinguishing cause from symptoms")
    supporting_evidence: List[SupportingEvidenceItem] = Field(default_factory=list)
    alternative_causes: List[str] = Field(default_factory=list)
    suggested_fix: str = Field(..., description="Step-by-step safe remediation instructions")
    kubectl_commands: List[KubectlCommandProposal] = Field(default_factory=list)
    yaml_proposal: Optional[str] = Field(None, description="Proposed YAML diff or manifest patch")
    prevention_recommendations: List[str] = Field(default_factory=list)
    confidence: int = Field(..., ge=0, le=100, description="Confidence score from 0 to 100")
    confidence_level: str = Field("medium", description="Confidence tier: low, medium, or high")
    evidence_gaps: List[str] = Field(default_factory=list, description="Missing or ambiguous signals")