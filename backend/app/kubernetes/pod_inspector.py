"""
KubeVora - Pod Inspector
Collects and detects unhealthy pods and container failure states.
"""
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from loguru import logger
from app.core.config import settings
from app.kubernetes.kubectl_executor import KubectlExecutor, kubectl_executor

FAILURE_REASONS = {
    "CrashLoopBackOff",
    "ImagePullBackOff",
    "ErrImagePull",
    "OOMKilled",
    "Error",
    "CreateContainerConfigError",
    "CreateContainerError",
}


class PodInspector:
    def __init__(self, executor: Optional[KubectlExecutor] = None):
        self.executor = executor or kubectl_executor
        self.stuck_threshold = settings.KUBEVORA_STUCK_THRESHOLD_SECONDS

    def inspect_pods(self, namespace: Optional[str] = None) -> Dict[str, Any]:
        """Inspect pods and isolate problematic workloads."""
        args = ["get", "pods", "-o", "json"]
        if namespace and namespace != "all-namespaces":
            if not self.executor.validate_name(namespace):
                return {
                    "healthy": False,
                    "error": f"Invalid namespace name: {namespace}",
                    "total_pods": 0,
                    "problematic_pods": [],
                }
            args.extend(["-n", namespace])
        else:
            args.append("-A")

        res = self.executor.execute(args, parse_json=True)
        if not res.success or not res.data:
            return {
                "healthy": False,
                "error": res.error_message or "Failed to query pods",
                "total_pods": 0,
                "problematic_pods": [],
            }

        items = res.data.get("items", [])
        problematic_pods = []
        now = datetime.now(timezone.utc)

        for pod in items:
            metadata = pod.get("metadata", {})
            status = pod.get("status", {})
            pod_name = metadata.get("name", "unknown")
            pod_ns = metadata.get("namespace", "default")
            phase = status.get("phase", "Unknown")

            container_statuses = status.get("containerStatuses", []) + status.get("initContainerStatuses", [])
            pod_issues = []
            max_restarts = 0

            # 1. Analyze container states
            for cs in container_statuses:
                c_name = cs.get("name", "")
                restarts = cs.get("restartCount", 0)
                if restarts > max_restarts:
                    max_restarts = restarts

                state = cs.get("state", {})
                last_state = cs.get("lastState", {})
                is_running = bool(state.get("running"))

                # Waiting state check
                waiting = state.get("waiting")
                if waiting:
                    reason = waiting.get("reason", "")
                    msg = waiting.get("message", "")
                    if reason in FAILURE_REASONS:
                        pod_issues.append({
                            "container": c_name,
                            "state": "waiting",
                            "reason": reason,
                            "message": msg,
                            "restart_count": restarts,
                        })
                    elif reason == "ContainerCreating":
                        # Check if stuck creating container beyond threshold
                        created_str = metadata.get("creationTimestamp")
                        if created_str:
                            try:
                                created_dt = datetime.fromisoformat(created_str.replace("Z", "+00:00"))
                                age_seconds = (now - created_dt).total_seconds()
                                if age_seconds > self.stuck_threshold:
                                    pod_issues.append({
                                        "container": c_name,
                                        "state": "waiting",
                                        "reason": "ContainerCreating (stuck)",
                                        "message": f"Container stuck creating for {int(age_seconds)}s",
                                        "restart_count": restarts,
                                    })
                            except Exception:
                                pass

                # Terminated state check: check current terminated state, or lastState only if not actively running
                terminated = state.get("terminated") or (last_state.get("terminated") if not is_running else None)
                if terminated:
                    reason = terminated.get("reason", "")
                    exit_code = terminated.get("exitCode", 0)
                    msg = terminated.get("message", "")
                    if reason in FAILURE_REASONS or exit_code != 0:
                        pod_issues.append({
                            "container": c_name,
                            "state": "terminated",
                            "reason": reason or ("OOMKilled" if exit_code == 137 else f"ExitCode_{exit_code}"),
                            "exit_code": exit_code,
                            "message": msg or f"Container terminated with exit code {exit_code}",
                            "restart_count": restarts,
                        })

            # 2. Check Pod phase if not already flagged
            if not pod_issues and phase in ("Failed", "Unknown"):
                pod_issues.append({
                    "container": "pod",
                    "state": phase.lower(),
                    "reason": status.get("reason", phase),
                    "message": status.get("message", f"Pod is in {phase} phase"),
                    "restart_count": max_restarts,
                })

            if pod_issues:
                primary_issue = pod_issues[0]
                problematic_pods.append({
                    "name": pod_name,
                    "namespace": pod_ns,
                    "phase": phase,
                    "status": primary_issue["reason"],
                    "restart_count": max_restarts,
                    "reason": primary_issue["reason"],
                    "message": primary_issue.get("message", ""),
                    "containers": pod_issues,
                })

        return {
            "healthy": len(problematic_pods) == 0,
            "total_pods": len(items),
            "problematic_pods_count": len(problematic_pods),
            "problematic_pods": problematic_pods,
        }


pod_inspector = PodInspector()

