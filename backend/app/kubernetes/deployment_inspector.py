"""
KubeVora - Deployment Inspector
Inspects rollout status, replica health, and failure conditions.
"""
from typing import Any, Dict, List, Optional
from app.kubernetes.kubectl_executor import KubectlExecutor, kubectl_executor


class DeploymentInspector:
    def __init__(self, executor: Optional[KubectlExecutor] = None):
        self.executor = executor or kubectl_executor

    def inspect_deployments(self, namespace: Optional[str] = None) -> Dict[str, Any]:
        args = ["get", "deployments", "-o", "json"]
        if namespace and namespace != "all-namespaces":
            args.extend(["-n", namespace])
        else:
            args.append("-A")

        res = self.executor.execute(args, parse_json=True)
        if not res.success or not res.data:
            return {
                "healthy": False,
                "error": res.error_message or "Failed to query deployments",
                "deployments": [],
            }

        items = res.data.get("items", [])
        deployments = []
        unhealthy_count = 0

        for d in items:
            name = d.get("metadata", {}).get("name", "")
            ns = d.get("metadata", {}).get("namespace", "default")
            spec = d.get("spec", {})
            status = d.get("status", {})

            desired = spec.get("replicas", 1)
            ready = status.get("readyReplicas", 0)
            available = status.get("availableReplicas", 0)
            updated = status.get("updatedReplicas", 0)

            conditions = status.get("conditions", [])
            issues = []

            # If deliberately scaled to zero, do not flag as an incident
            if desired == 0:
                is_healthy = True
            else:
                if ready < desired:
                    issues.append(f"Only {ready}/{desired} replicas are ready")
                for c in conditions:
                    c_type = c.get("type", "")
                    c_status = c.get("status", "")
                    c_reason = c.get("reason", "")
                    c_msg = c.get("message", "")
                    if c_type == "Progressing" and c_status == "False":
                        issues.append(f"Rollout stalled: {c_reason} - {c_msg}")
                    if c_reason == "ProgressDeadlineExceeded":
                        issues.append("Rollout exceeded progress deadline")

                is_healthy = len(issues) == 0

            if not is_healthy:
                unhealthy_count += 1

            deployments.append({
                "name": name,
                "namespace": ns,
                "healthy": is_healthy,
                "desired_replicas": desired,
                "ready_replicas": ready,
                "available_replicas": available,
                "updated_replicas": updated,
                "issues": issues,
            })

        return {
            "healthy": unhealthy_count == 0,
            "total_deployments": len(items),
            "unhealthy_count": unhealthy_count,
            "deployments": deployments,
        }