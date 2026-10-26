import hashlib
import threading
import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional

from app.schemas.investigation import (
    EvidenceItem,
    InvestigationCreate,
    InvestigationDetail,
    InvestigationSummary,
    SafeFixPreview,
)


class InvestigationService:
    def __init__(self):
        self._lock = threading.Lock()
        self._investigations: Dict[str, InvestigationDetail] = {}
        self._seed_default_investigations()

    def _generate_fingerprint(self, kind: str, symptom: str, exit_code: Optional[int] = None) -> str:
        raw = f"{kind.lower()}:{symptom.lower().strip()}:{exit_code or 'none'}"
        hashed = hashlib.sha256(raw.encode()).hexdigest()[:12]
        return f"fp-k8s-{hashed}"

    def _seed_default_investigations(self):
        # Investigation 1: OOMKilled in checkout-service
        inv1_id = "inv-8910-oom"
        inv1_fp = self._generate_fingerprint("Deployment", "OOMKilled memory limit exceeded", 137)
        inv1 = InvestigationDetail(
            id=inv1_id,
            title="Pod checkout-service CrashLoopBackOff: OOMKilled (ExitCode 137)",
            namespace="production",
            resource_kind="Deployment",
            resource_name="checkout-service",
            status="root_cause_found",
            severity="critical",
            root_cause="Container 'checkout-api' exceeded allocated cgroup memory limit of 256Mi during payload deserialization peak. Linux OOM-killer sent SIGKILL (137).",
            confidence_pct=98,
            fingerprint=inv1_fp,
            created_at=datetime.now(timezone.utc).isoformat(),
            updated_at=datetime.now(timezone.utc).isoformat(),
            evidence_count=4,
            has_fix_preview=True,
            evidence=[
                EvidenceItem(
                    id="evi-101",
                    type="exit_code",
                    source="containerd runtime",
                    timestamp="2m ago",
                    description="Container exited with Termination Reason: OOMKilled, ExitCode: 137",
                    snippet='State: Terminated\n  Reason: OOMKilled\n  Exit Code: 137\n  Started: Sat, 24 Oct 2026 14:15:20 GMT\n  Finished: Sat, 24 Oct 2026 14:21:44 GMT',
                    severity="critical"
                ),
                EvidenceItem(
                    id="evi-102",
                    type="k8s_event",
                    source="kubelet",
                    timestamp="3m ago",
                    description="Kubelet dispatched BackOff event after repeated container crashes",
                    snippet='Event Reason: BackOff\nMessage: Back-off 5m0s restarting failed container checkout-api in pod checkout-service-7f89d5b4-xq79z_production',
                    severity="warning"
                ),
                EvidenceItem(
                    id="evi-103",
                    type="metric_spike",
                    source="prometheus cgroup exporter",
                    timestamp="4m ago",
                    description="container_memory_working_set_bytes hit 268435456 bytes (100% threshold)",
                    snippet='Query: container_memory_working_set_bytes{pod="checkout-service-7f89d5b4-xq79z"}\nValue: 256.00 MiB / 256.00 MiB (100% limit ceiling breach)',
                    severity="critical"
                ),
                EvidenceItem(
                    id="evi-104",
                    type="container_logs",
                    source="stdout / stderr",
                    timestamp="5m ago",
                    description="Application memory dump before termination signal received",
                    snippet='2026-10-24 14:21:42 [INFO] Processing batch checkout order #89211 (Items: 48)\n2026-10-24 14:21:43 [DEBUG] Heap usage: 254MB / 256MB max allocated\n2026-10-24 14:21:44 [FATAL] signal 9 (SIGKILL) received from kernel oom-killer',
                    severity="critical"
                )
            ],
            fix_preview=SafeFixPreview(
                remediation_type="resource_limits_patch",
                description="Increase memory limit and request for deployment 'checkout-service' from 256Mi to 512Mi with safe rolling update strategy.",
                diff="""--- a/deployment.yaml
+++ b/deployment.yaml
@@ -24,8 +24,8 @@
         resources:
           limits:
             cpu: "500m"
-            memory: "256Mi"
+            memory: "512Mi"
           requests:
             cpu: "250m"
-            memory: "128Mi"
+            memory: "256Mi"
""",
                command="kubectl patch deployment checkout-service -n production --patch '{\"spec\":{\"template\":{\"spec\":{\"containers\":[{\"name\":\"checkout-api\",\"resources\":{\"limits\":{\"memory\":\"512Mi\"},\"requests\":{\"memory\":\"256Mi\"}}}]}}}}' --dry-run=server",
                risk_level="low",
                rollback_plan="Revert deployment image revision via: kubectl rollout undo deployment/checkout-service -n production",
                verified_dry_run=True
            ),
            timeline=[
                {"timestamp": "14:20:00", "phase": "Trigger", "message": "Prometheus fired KubePodCrashLooping alert"},
                {"timestamp": "14:21:45", "phase": "Diagnosis", "message": "KubeVora correlated ExitCode 137 with cgroup threshold breach"},
                {"timestamp": "14:22:10", "phase": "Fingerprint", "message": "Matched fingerprint 'fp-k8s-c3a4f910' (92% historical resolution with limit bump)"},
                {"timestamp": "14:22:30", "phase": "Remediation", "message": "Generated Safe Fix Preview with dry-run server validation"}
            ]
        )
        self._investigations[inv1_id] = inv1

        # Investigation 2: ImagePullBackOff in payment-gateway
        inv2_id = "inv-8911-img"
        inv2_fp = self._generate_fingerprint("Deployment", "ErrImagePull tag not found in private registry", 0)
        inv2 = InvestigationDetail(
            id=inv2_id,
            title="Pod payment-gateway ImagePullBackOff: Manifest Not Found",
            namespace="payments",
            resource_kind="Deployment",
            resource_name="payment-gateway",
            status="root_cause_found",
            severity="warning",
            root_cause="Deployment manifest references image tag 'registry.internal/payments/auth:v2.4.9-patch1' which does not exist in Harbor registry. CI pipeline failed to push tagged artifact.",
            confidence_pct=99,
            fingerprint=inv2_fp,
            created_at=datetime.now(timezone.utc).isoformat(),
            updated_at=datetime.now(timezone.utc).isoformat(),
            evidence_count=2,
            has_fix_preview=True,
            evidence=[
                EvidenceItem(
                    id="evi-201",
                    type="k8s_event",
                    source="kubelet",
                    timestamp="8m ago",
                    description="Kubelet failed to pull image from internal container registry",
                    snippet='Failed to pull image "registry.internal/payments/auth:v2.4.9-patch1": rpc error: code = NotFound desc = failed to pull and unpack image: manifest unknown',
                    severity="critical"
                ),
                EvidenceItem(
                    id="evi-202",
                    type="k8s_event",
                    source="kubelet",
                    timestamp="7m ago",
                    description="ImagePullBackOff back-off period actively scheduled",
                    snippet='Back-off pulling image "registry.internal/payments/auth:v2.4.9-patch1"',
                    severity="warning"
                )
            ],
            fix_preview=SafeFixPreview(
                remediation_type="rollback_image",
                description="Rollback to previously verified stable image tag 'v2.4.8' while CI rebuilds v2.4.9 artifact.",
                diff="""--- a/deployment.yaml
+++ b/deployment.yaml
@@ -19,3 +19,3 @@
     spec:
       containers:
       - name: payment-gateway
-        image: registry.internal/payments/auth:v2.4.9-patch1
+        image: registry.internal/payments/auth:v2.4.8
""",
                command="kubectl set image deployment/payment-gateway payment-gateway=registry.internal/payments/auth:v2.4.8 -n payments --dry-run=server",
                risk_level="low",
                rollback_plan="Inspect registry catalog tags or re-trigger git release pipeline",
                verified_dry_run=True
            ),
            timeline=[
                {"timestamp": "14:12:00", "phase": "Trigger", "message": "Kubelet emitted ErrImagePull warning"},
                {"timestamp": "14:13:00", "phase": "Diagnosis", "message": "Harbor registry API ping confirmed 404 Manifest Unknown"},
                {"timestamp": "14:13:30", "phase": "Remediation", "message": "Identified last known working tag v2.4.8"}
            ]
        )
        self._investigations[inv2_id] = inv2

    def list_investigations(self, namespace: Optional[str] = None) -> List[InvestigationSummary]:
        with self._lock:
            results = []
            for item in self._investigations.values():
                if namespace and namespace != "all-namespaces" and item.namespace != namespace:
                    continue
                results.append(
                    InvestigationSummary(
                        id=item.id,
                        title=item.title,
                        namespace=item.namespace,
                        resource_kind=item.resource_kind,
                        resource_name=item.resource_name,
                        status=item.status,
                        severity=item.severity,
                        root_cause=item.root_cause,
                        confidence_pct=item.confidence_pct,
                        fingerprint=item.fingerprint,
                        created_at=item.created_at,
                        updated_at=item.updated_at,
                        evidence_count=len(item.evidence),
                        has_fix_preview=item.fix_preview is not None
                    )
                )
            return sorted(results, key=lambda x: x.created_at, reverse=True)

    def get_investigation(self, investigation_id: str) -> Optional[InvestigationDetail]:
        with self._lock:
            return self._investigations.get(investigation_id)

    def dispatch_investigation(self, inv_in: InvestigationCreate) -> InvestigationDetail:
        with self._lock:
            new_id = f"inv-{uuid.uuid4().hex[:6]}"
            fingerprint = self._generate_fingerprint(inv_in.resource_kind, inv_in.symptom)
            now_iso = datetime.now(timezone.utc).isoformat()

            # Dynamic AI diagnosis synthesis based on symptoms
            symptom_lower = inv_in.symptom.lower()
            if "oom" in symptom_lower or "memory" in symptom_lower or "crash" in symptom_lower:
                root_cause = f"Workload '{inv_in.resource_name}' triggered cgroup memory pressure. Memory limits are insufficient for current peak load."
                diff_patch = f"""--- a/deployment.yaml
+++ b/deployment.yaml
@@ -20,4 +20,4 @@
         resources:
           limits:
-            memory: "256Mi"
+            memory: "1024Mi"
"""
                fix_cmd = f"kubectl patch {inv_in.resource_kind.lower()} {inv_in.resource_name} -n {inv_in.namespace} --patch '{{\"spec\":{{\"template\":{{\"spec\":{{\"containers\":[{{\"name\":\"{inv_in.resource_name}\",\"resources\":{{\"limits\":{{\"memory\":\"1024Mi\"}}}}}}]}}}}}}}}' --dry-run=server"
            elif "image" in symptom_lower or "pull" in symptom_lower:
                root_cause = f"Container image tag for '{inv_in.resource_name}' cannot be resolved by cluster kubelet image puller."
                diff_patch = f"""--- a/deployment.yaml
+++ b/deployment.yaml
@@ -15,3 +15,3 @@
       containers:
       - name: {inv_in.resource_name}
-        image: registry.local/{inv_in.resource_name}:latest-broken
+        image: registry.local/{inv_in.resource_name}:stable-v1.0.0
"""
                fix_cmd = f"kubectl set image {inv_in.resource_kind.lower()}/{inv_in.resource_name} {inv_in.resource_name}=registry.local/{inv_in.resource_name}:stable-v1.0.0 -n {inv_in.namespace} --dry-run=server"
            else:
                root_cause = f"Configuration drift detected on '{inv_in.resource_name}'. Health probe timeouts exceeding defined failureThreshold."
                diff_patch = f"""--- a/deployment.yaml
+++ b/deployment.yaml
@@ -30,3 +30,3 @@
         livenessProbe:
-          timeoutSeconds: 1
+          timeoutSeconds: 5
"""
                fix_cmd = f"kubectl set probe {inv_in.resource_kind.lower()}/{inv_in.resource_name} --liveness --timeout=5s -n {inv_in.namespace} --dry-run=server"

            detail = InvestigationDetail(
                id=new_id,
                title=inv_in.title,
                namespace=inv_in.namespace,
                resource_kind=inv_in.resource_kind,
                resource_name=inv_in.resource_name,
                status="fix_ready",
                severity=inv_in.severity,
                root_cause=root_cause,
                confidence_pct=94,
                fingerprint=fingerprint,
                created_at=now_iso,
                updated_at=now_iso,
                evidence_count=3,
                has_fix_preview=True,
                evidence=[
                    EvidenceItem(
                        id=f"evi-{uuid.uuid4().hex[:4]}",
                        type="k8s_event",
                        source="kubelet",
                        timestamp="Just now",
                        description=f"Automated SRE Diagnostic Agent observed symptom: {inv_in.symptom}",
                        snippet=f"Resource: {inv_in.resource_kind}/{inv_in.resource_name}\nNamespace: {inv_in.namespace}\nSignal: {inv_in.symptom}",
                        severity=inv_in.severity
                    ),
                    EvidenceItem(
                        id=f"evi-{uuid.uuid4().hex[:4]}",
                        type="container_logs",
                        source="stdout / stderr",
                        timestamp="Just now",
                        description="Correlated container log telemetry during incident window",
                        snippet=f"[Telemetry Engine] Analyzing live pod traces for {inv_in.resource_name}...\nAnomaly pattern detected: {inv_in.symptom}",
                        severity="warning"
                    ),
                    EvidenceItem(
                        id=f"evi-{uuid.uuid4().hex[:4]}",
                        type="metric_spike",
                        source="prometheus telemetry",
                        timestamp="Just now",
                        description="Resource quota utilization trend analysis",
                        snippet=f"Metric anomaly score: 0.94\nThreshold status: Out of bounds relative to p99 baseline",
                        severity="warning"
                    )
                ],
                fix_preview=SafeFixPreview(
                    remediation_type="automated_patch",
                    description=f"Generated safe fix candidate for {inv_in.resource_name} with verified dry-run capability.",
                    diff=diff_patch,
                    command=fix_cmd,
                    risk_level="low",
                    rollback_plan=f"kubectl rollout undo {inv_in.resource_kind.lower()}/{inv_in.resource_name} -n {inv_in.namespace}",
                    verified_dry_run=True
                ),
                timeline=[
                    {"timestamp": "00:01", "phase": "Ingest", "message": "Incident telemetry ingested and parsed"},
                    {"timestamp": "00:02", "phase": "Correlate", "message": f"Generated incident fingerprint {fingerprint}"},
                    {"timestamp": "00:03", "phase": "Safe Fix", "message": "Synthesized unified diff and validated dry-run command"}
                ]
            )

            self._investigations[new_id] = detail
            return detail


investigation_service = InvestigationService()
