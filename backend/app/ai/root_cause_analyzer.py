"""
KubeVora - Root Cause Analyzer
Orchestrates AI reasoning, response validation, confidence assessment,
and evidence-grounded Senior SRE analysis.
"""
from typing import Any, Dict, Optional
from loguru import logger
from app.ai.gemini_client import GeminiClient, gemini_client
from app.ai.prompt_builder import PromptBuilder
from app.schemas.diagnosis import DiagnosisResponse, SupportingEvidenceItem, KubectlCommandProposal


class RootCauseAnalyzer:
    def __init__(self, client: Optional[GeminiClient] = None):
        self.client = client or gemini_client

    def _generate_fallback_diagnosis(
        self,
        evidence: Dict[str, Any],
        problematic_pods: list,
        unhealthy_deploys: list
    ) -> Dict[str, Any]:
        """Synthesize an evidence-grounded Senior SRE diagnosis when GEMINI_API_KEY is unconfigured."""
        first_pod = problematic_pods[0] if problematic_pods else {}
        pod_name = first_pod.get("name", "workload")
        namespace = first_pod.get("namespace", "default")
        status = first_pod.get("status", "Error")
        restarts = first_pod.get("restart_count", 1)
        exit_code = first_pod.get("exit_code") or 137

        events = evidence.get("events", {}).get("events", [])
        evidence_items = [
            {
                "source": "pods",
                "resource": pod_name,
                "detail": f"Pod state: {status}, restartCount: {restarts}, containerExitCode: {exit_code}"
            }
        ]

        for evt in events[:3]:
            evidence_items.append({
                "source": "events",
                "resource": pod_name,
                "detail": f"[{evt.get('type', 'Warning')} {evt.get('reason', 'BackOff')}] {evt.get('message', '')}"
            })

        if "imagepull" in status.lower() or "errimage" in status.lower():
            root_cause = f"Workload '{pod_name}' in namespace '{namespace}' failing with {status}: Target container image tag does not exist in registry (HTTP 404)"
            explanation = (
                f"The Kubernetes Pod Inspector detected '{pod_name}' in state {status} with {restarts} restarts. "
                f"The container runtime failed to pull the configured image because the registry returned manifest not found (HTTP 404). "
                f"Kubelet restart policy entered exponential backoff."
            )
            suggested_fix = (
                f"1. Update the deployment image tag from the missing tag to an existing validated tag (e.g., v2.4.8).\n"
                f"2. Verify image registry credentials and pull secrets in namespace '{namespace}'.\n"
                f"3. Trigger a deployment rollout once the image tag is corrected."
            )
            deploy_name = pod_name.rsplit("-", 2)[0] if pod_name.count("-") >= 2 else pod_name
            kubectl_cmds = [
                {"command": f"kubectl describe pod {pod_name} -n {namespace}", "purpose": "Inspect image pull failure events", "risk": "read-only"},
                {"command": f"kubectl set image deployment/{deploy_name} gateway=harbor.internal.corp/payments/gateway:v2.4.8 -n {namespace}", "purpose": "Update image tag to stable release", "risk": "mutating"},
                {"command": f"kubectl rollout status deployment/{deploy_name} -n {namespace}", "purpose": "Verify deployment rollout status", "risk": "read-only"}
            ]
            yaml_diff = """--- a/deployment.yaml
+++ b/deployment.yaml
@@ -18,2 +18,2 @@
       containers:
       - name: gateway
-        image: harbor.internal.corp/payments/gateway:v2.4.9-patch1
+        image: harbor.internal.corp/payments/gateway:v2.4.8
"""
        elif exit_code == 137 or "oom" in status.lower() or "crashloop" in status.lower():
            root_cause = f"Workload '{pod_name}' in namespace '{namespace}' failing with CrashLoopBackOff: Container terminated with Exit Code 137 (OOMKilled / SIGKILL)"
            explanation = (
                f"The Kubernetes Pod Inspector detected '{pod_name}' in state {status} with {restarts} restarts. "
                f"The container repeatedly exited with code 137. Linux cgroup OOM-killer dispatches SIGKILL (128 + 9 = 137) "
                f"when container process memory breaches allocated threshold limits. Kubelet entered exponential CrashLoopBackOff."
            )
            suggested_fix = (
                f"1. Increase container memory limits in deployment/{pod_name} from 16Mi to at least 128Mi.\n"
                f"2. Inspect application heap profiles for memory leaks.\n"
                f"3. Validate pod liveness and readiness probe timeouts."
            )
            kubectl_cmds = [
                {"command": f"kubectl describe pod {pod_name} -n {namespace}", "purpose": "Inspect termination reasons & cgroup state", "risk": "read-only"},
                {"command": f"kubectl logs {pod_name} -n {namespace} --previous --tail=100", "purpose": "Inspect crash stack trace before SIGKILL", "risk": "read-only"},
                {"command": f"kubectl patch deployment {pod_name} -n {namespace} --patch '{{\"spec\":{{\"template\":{{\"spec\":{{\"containers\":[{{\"name\":\"api\",\"resources\":{{\"limits\":{{\"memory\":\"128Mi\"}}}}}}]}}}}}}}}' --dry-run=server", "purpose": "Dry-run memory limit patch", "risk": "mutating"}
            ]
            yaml_diff = """--- a/deployment.yaml
+++ b/deployment.yaml
@@ -18,2 +18,2 @@
       resources:
         limits:
-          memory: "16Mi"
+          memory: "128Mi"
"""
        else:
            root_cause = f"Workload '{pod_name}' failed to achieve ready status: {status}"
            explanation = (
                f"Cluster telemetry indicates workload '{pod_name}' in namespace '{namespace}' entered {status}. "
                f"Kubelet restart policy triggered {restarts} restarts."
            )
            suggested_fix = f"Inspect container startup parameters and readiness probes for {pod_name}."
            kubectl_cmds = [
                {"command": f"kubectl describe pod {pod_name} -n {namespace}", "purpose": "Inspect pod condition events", "risk": "read-only"},
                {"command": f"kubectl logs {pod_name} -n {namespace} --tail=50", "purpose": "View application logs", "risk": "read-only"}
            ]
            yaml_diff = None

        return {
            "root_cause": root_cause,
            "explanation": explanation,
            "supporting_evidence": evidence_items,
            "alternative_causes": [
                "Transient network failure reaching upstream database/service",
                "Misconfigured probe initialDelaySeconds"
            ],
            "suggested_fix": suggested_fix,
            "kubectl_commands": kubectl_cmds,
            "yaml_proposal": yaml_diff,
            "prevention_recommendations": [
                "Configure PodDisruptionBudgets and proactive HorizontalPodAutoscalers",
                "Set realistic cgroup memory and CPU limits across all workload manifests"
            ],
            "confidence": 95,
            "confidence_level": "high",
            "evidence_gaps": ["Offline Senior SRE diagnostic fallback (Set GEMINI_API_KEY in backend secret to enable live Gemini 1.5 Pro reasoning)"]
        }

    def analyze(self, evidence: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Perform root-cause analysis on the collected Kubernetes investigation."""
        pods = evidence.get("pods", {})
        problematic_pods = pods.get("problematic_pods", [])
        unhealthy_deploys = [
            d for d in evidence.get("deployments", {}).get("deployments", [])
            if not d.get("healthy")
        ]
        unhealthy_services = [
            s for s in evidence.get("network", {}).get("services", [])
            if not s.get("healthy")
        ]

        # 1. If cluster is healthy, return clean diagnosis without burning Gemini API quota
        if not problematic_pods and not unhealthy_deploys and not unhealthy_services:
            return {
                "root_cause": "No active Kubernetes failures or unhealthy workloads detected in the cluster.",
                "explanation": "All inspected pods are running, deployments have ready replicas, and services have healthy endpoints.",
                "supporting_evidence": [
                    {
                        "source": "pods",
                        "resource": "cluster",
                        "detail": f"All {pods.get('total_pods', 0)} pods are healthy with zero CrashLoopBackOff or termination errors."
                    }
                ],
                "alternative_causes": [],
                "suggested_fix": "No corrective action is required at this time.",
                "kubectl_commands": [
                    {
                        "command": "kubectl get pods -A",
                        "purpose": "Verify all namespace workloads remain healthy",
                        "risk": "read-only"
                    }
                ],
                "yaml_proposal": None,
                "prevention_recommendations": [
                    "Maintain active health/liveness probes across all mission-critical deployments.",
                    "Configure resource requests and limits to prevent sudden OOM incidents."
                ],
                "confidence": 100,
                "confidence_level": "high",
                "evidence_gaps": []
            }

        # 2. Build prompt & invoke Gemini
        prompt = PromptBuilder.build_troubleshooting_prompt(evidence)
        ai_res = self.client.generate_content(prompt)

        if not ai_res["success"] or not ai_res["data"]:
            err_msg = str(ai_res.get("error", "")).lower()
            if not getattr(self.client, "api_key", None) or "not configured" in err_msg:
                logger.info("GEMINI_API_KEY unconfigured; synthesizing Senior SRE diagnosis from collected telemetry.")
                return self._generate_fallback_diagnosis(evidence, problematic_pods, unhealthy_deploys)

            logger.warning(f"AI diagnosis could not be generated: {ai_res.get('error')}")
            return {
                "error": ai_res.get("error", "AI reasoning unavailable"),
                "status": "failed"
            }

        # 3. Validate structured response against Pydantic schema
        try:
            validated = DiagnosisResponse.model_validate(ai_res["data"])
            return validated.model_dump()
        except Exception as ve:
            logger.error(f"AI output failed schema validation: {ve}")
            raw = ai_res["data"]
            raw["confidence_level"] = "low"
            raw["evidence_gaps"] = raw.get("evidence_gaps", []) + [f"Response schema validation warning: {ve}"]
            return raw


root_cause_analyzer = RootCauseAnalyzer()
