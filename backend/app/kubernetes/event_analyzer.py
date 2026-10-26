"""
KubeVora - Events Analyzer
Analyzes Kubernetes cluster and namespace events for troubleshooting signals.
"""
from typing import Any, Dict, List, Optional
from app.kubernetes.kubectl_executor import KubectlExecutor, kubectl_executor

FAILURE_EVENT_REASONS = {
    "FailedScheduling", "BackOff", "FailedMount", "FailedPull",
    "ErrImagePull", "Unhealthy", "FailedCreate", "Failed",
    "Killing", "NodeNotReady"
}


class EventsAnalyzer:
    def __init__(self, executor: Optional[KubectlExecutor] = None):
        self.executor = executor or kubectl_executor

    def analyze_events(
        self,
        namespace: Optional[str] = None,
        involved_pod_names: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Fetch and structure relevant Kubernetes events."""
        args = ["get", "events", "-o", "json"]
        if namespace and namespace != "all-namespaces":
            args.extend(["-n", namespace])
        else:
            args.append("-A")

        res = self.executor.execute(args, parse_json=True)
        if not res.success or not res.data:
            return {
                "total_events": 0,
                "warning_events_count": 0,
                "events": [],
                "error": res.error_message or "Failed to query events",
            }

        items = res.data.get("items", [])
        pod_names_set = set(involved_pod_names or [])
        events = []
        warning_count = 0

        for it in items:
            event_type = it.get("type", "Normal")
            reason = it.get("reason", "")
            message = it.get("message", "")
            involved = it.get("involvedObject", {})
            res_kind = involved.get("kind", "")
            res_name = involved.get("name", "")
            res_ns = involved.get("namespace", namespace or "default")
            count = it.get("count", 1)
            last_timestamp = it.get("lastTimestamp") or it.get("eventTime") or ""

            # Prioritize Warning events or events directly related to problematic pods
            is_warning = event_type == "Warning" or reason in FAILURE_EVENT_REASONS
            matches_pod = res_name in pod_names_set if pod_names_set else True

            if is_warning or (matches_pod and reason in FAILURE_EVENT_REASONS):
                if is_warning:
                    warning_count += 1

                events.append({
                    "type": event_type,
                    "reason": reason,
                    "involved_resource": f"{res_kind}/{res_name}",
                    "namespace": res_ns,
                    "message": message,
                    "count": count,
                    "timestamp": last_timestamp,
                })

        # Return top 30 most critical events
        return {
            "total_events": len(items),
            "warning_events_count": warning_count,
            "relevant_events_count": len(events),
            "events": events[:30],
        }