"""
KubeVora - Persistence Service
Handles database transactions for investigations, findings, and incident fingerprints.
"""
import hashlib
import json
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from sqlalchemy.orm import Session
from loguru import logger

from app.models.investigation import Investigation
from app.models.finding import Finding
from app.models.fingerprint import IncidentFingerprint


class PersistenceService:
    @staticmethod
    def generate_fingerprint_hash(
        namespace: str,
        resource_kind: str,
        resource_name: str,
        failure_category: str,
        normalized_error: str,
    ) -> str:
        """
        Generate a deterministic incident fingerprint hash.
        Normalizes timestamps, pod hashes, and memory addresses before hashing.
        """
        # Normalize: strip pod hex/random suffixes (e.g., payment-service-7f9b8c64-kx29z -> payment-service)
        norm_name = re.sub(r"-[a-z0-9]{8,10}-[a-z0-9]{4,5}$", "", resource_name.lower())
        # Normalize: strip timestamps and hex addresses from error strings
        norm_err = re.sub(r"0x[0-9a-fA-F]+", "0xADDR", normalized_error.lower())
        norm_err = re.sub(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?Z?", "", norm_err).strip()

        raw_signature = f"{namespace.lower()}:{resource_kind.lower()}:{norm_name}:{failure_category.lower()}:{norm_err[:80]}"
        return hashlib.sha256(raw_signature.encode("utf-8")).hexdigest()[:16]

    def create_investigation(
        self,
        db: Session,
        user_id: str,
        cluster_context: str = "default",
        namespace: str = "default",
    ) -> Investigation:
        """Create a new running investigation record associated with the user."""
        inv = Investigation(
            user_id=user_id,
            cluster_context=cluster_context,
            namespace=namespace,
            status="running",
            created_at=datetime.now(timezone.utc),
        )
        db.add(inv)
        db.commit()
        db.refresh(inv)
        return inv

    def record_findings(
        self,
        db: Session,
        investigation_id: str,
        evidence: Dict[str, Any],
    ) -> List[Finding]:
        """Extract structured findings from investigation evidence and persist them."""
        findings: List[Finding] = []

        # 1. Pod findings
        problematic_pods = evidence.get("pods", {}).get("problematic_pods", [])
        for p in problematic_pods:
            p_name = p.get("name", "unknown")
            p_ns = p.get("namespace", "default")
            status = p.get("status", "Degraded")
            msg = p.get("message", f"Pod in {status} state")

            finding = Finding(
                investigation_id=investigation_id,
                category="pod",
                resource_kind="Pod",
                resource_name=p_name,
                namespace=p_ns,
                severity="critical" if status in ("CrashLoopBackOff", "OOMKilled") else "warning",
                summary=f"Pod {p_name} is unhealthy: {status}",
                evidence_detail=p,
            )
            findings.append(finding)
            db.add(finding)

        # 2. Log findings
        collected_logs = evidence.get("logs", {}).get("collected_logs", [])
        for log_set in collected_logs:
            if log_set.get("error_detected"):
                pod_name = log_set.get("pod", "")
                pod_ns = log_set.get("namespace", "default")
                lines = log_set.get("relevant_lines", [])
                summary_line = lines[0] if lines else "Errors detected in logs"

                finding = Finding(
                    investigation_id=investigation_id,
                    category="log",
                    resource_kind="Pod",
                    resource_name=pod_name,
                    namespace=pod_ns,
                    severity="critical",
                    summary=f"Application log error in {pod_name}: {summary_line[:150]}",
                    evidence_detail={"relevant_lines": lines, "source": log_set.get("source")},
                )
                findings.append(finding)
                db.add(finding)

        # 3. Deployment findings
        deployments = evidence.get("deployments", {}).get("deployments", [])
        for d in deployments:
            if not d.get("healthy"):
                d_name = d.get("name", "")
                d_ns = d.get("namespace", "default")
                issues = d.get("issues", [])

                finding = Finding(
                    investigation_id=investigation_id,
                    category="deployment",
                    resource_kind="Deployment",
                    resource_name=d_name,
                    namespace=d_ns,
                    severity="warning",
                    summary=f"Deployment {d_name} degraded: {', '.join(issues)}",
                    evidence_detail=d,
                )
                findings.append(finding)
                db.add(finding)

        # 4. Service / Network findings
        services = evidence.get("network", {}).get("services", [])
        for s in services:
            if not s.get("healthy"):
                s_name = s.get("name", "")
                s_ns = s.get("namespace", "default")
                issues = s.get("issues", [])

                finding = Finding(
                    investigation_id=investigation_id,
                    category="network",
                    resource_kind="Service",
                    resource_name=s_name,
                    namespace=s_ns,
                    severity="warning",
                    summary=f"Service {s_name} issue: {', '.join(issues)}",
                    evidence_detail=s,
                )
                findings.append(finding)
                db.add(finding)

        db.commit()
        return findings

    def record_or_update_fingerprint(
        self,
        db: Session,
        user_id: str,
        namespace: str,
        evidence: Dict[str, Any],
        diagnosis: Optional[Dict[str, Any]],
        investigation_id: str,
    ) -> Optional[str]:
        """
        Derive incident fingerprint, track recurrence count, and persist it.
        Returns the fingerprint hash string.
        """
        problematic_pods = evidence.get("pods", {}).get("problematic_pods", [])
        if not problematic_pods:
            return None

        primary_pod = problematic_pods[0]
        p_name = primary_pod.get("name", "unknown")
        failure_cat = primary_pod.get("status", "UnknownFailure")
        raw_err = primary_pod.get("message", "")

        # Try to use relevant log line if available
        collected_logs = evidence.get("logs", {}).get("collected_logs", [])
        for l in collected_logs:
            if l.get("relevant_lines"):
                raw_err = l["relevant_lines"][0]
                break

        fp_hash = self.generate_fingerprint_hash(
            namespace=namespace,
            resource_kind="Pod",
            resource_name=p_name,
            failure_category=failure_cat,
            normalized_error=raw_err,
        )

        now = datetime.now(timezone.utc)
        existing_fp = db.query(IncidentFingerprint).filter(
            IncidentFingerprint.fingerprint_hash == fp_hash
        ).first()

        if existing_fp:
            existing_fp.occurrence_count += 1
            existing_fp.last_observed_at = now
            existing_fp.last_investigation_id = investigation_id
            logger.info(f"Recurring incident detected! Fingerprint: {fp_hash} (Count: {existing_fp.occurrence_count})")
        else:
            new_fp = IncidentFingerprint(
                user_id=user_id,
                fingerprint_hash=fp_hash,
                failure_category=failure_cat,
                resource_kind="Pod",
                resource_name=p_name,
                namespace=namespace,
                first_observed_at=now,
                last_observed_at=now,
                occurrence_count=1,
                last_investigation_id=investigation_id,
            )
            db.add(new_fp)
            logger.info(f"New incident fingerprint created: {fp_hash}")

        db.commit()
        return fp_hash

    def finalize_investigation(
        self,
        db: Session,
        investigation_id: str,
        evidence: Dict[str, Any],
        diagnosis: Optional[Dict[str, Any]],
        duration_seconds: float,
        status: str = "completed",
        error_summary: Optional[str] = None,
        fingerprint_hash: Optional[str] = None,
    ) -> Investigation:
        """Update and finalize the investigation record with complete findings and diagnosis."""
        inv = db.query(Investigation).filter(Investigation.id == investigation_id).first()
        if not inv:
            raise ValueError(f"Investigation {investigation_id} not found in database")

        inv.status = status
        inv.completed_at = datetime.now(timezone.utc)
        inv.duration_seconds = duration_seconds
        inv.error_summary = error_summary
        if fingerprint_hash:
            inv.fingerprint_hash = fingerprint_hash

        if evidence:
            # Store compact telemetry summary rather than giant raw logs
            compact_evidence = {
                "pods_count": evidence.get("pods", {}).get("total_pods", 0),
                "problematic_pods": evidence.get("pods", {}).get("problematic_pods", []),
                "warning_events_count": evidence.get("events", {}).get("warning_events_count", 0),
                "unhealthy_deployments_count": evidence.get("deployments", {}).get("unhealthy_count", 0),
                "unhealthy_services_count": evidence.get("network", {}).get("unhealthy_count", 0),
            }
            inv.raw_evidence = compact_evidence

        if diagnosis:
            inv.root_cause = diagnosis.get("root_cause")
            inv.explanation = diagnosis.get("explanation")
            inv.confidence = diagnosis.get("confidence", 0)
            inv.confidence_level = diagnosis.get("confidence_level", "medium")
            inv.suggested_fix = diagnosis.get("suggested_fix")
            inv.kubectl_commands = diagnosis.get("kubectl_commands")
            inv.yaml_proposal = diagnosis.get("yaml_proposal")
            inv.prevention_recommendations = diagnosis.get("prevention_recommendations")
            inv.evidence_gaps = diagnosis.get("evidence_gaps")

        db.commit()
        db.refresh(inv)
        return inv

    def list_user_investigations(
        self,
        db: Session,
        user_id: str,
        limit: int = 50,
        cluster_id: Optional[str] = None,
        namespace: Optional[str] = None,
    ) -> List[Investigation]:
        """Retrieve user-specific investigations, ordered newest first."""
        query = db.query(Investigation).filter(Investigation.user_id == user_id)
        if cluster_id and cluster_id != "all":
            query = query.filter(Investigation.cluster_context == cluster_id)
        if namespace and namespace != "all-namespaces":
            query = query.filter(Investigation.namespace == namespace)
        return query.order_by(Investigation.created_at.desc()).limit(limit).all()

    def get_user_investigation(
        self,
        db: Session,
        user_id: str,
        investigation_id: str,
    ) -> Optional[Investigation]:
        """Retrieve a specific investigation, strictly enforcing user ownership."""
        return db.query(Investigation).filter(
            Investigation.id == investigation_id,
            Investigation.user_id == user_id,
        ).first()


persistence_service = PersistenceService()
