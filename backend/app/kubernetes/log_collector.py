"""
KubeVora - Logs Collector
Safely collects and sanitizes container logs for troubleshooting.
"""
import re
from typing import Any, Dict, List, Optional
from loguru import logger
from app.core.config import settings
from app.kubernetes.kubectl_executor import KubectlExecutor, kubectl_executor

# Redaction patterns for security
REDACTION_PATTERNS = [
    (re.compile(r"(Bearer\s+)[A-Za-z0-9\-_=]+\.[A-Za-z0-9\-_=]+\.?[A-Za-z0-9\-_=]*", re.I), r"\1[REDACTED_JWT]"),
    (re.compile(r"(password[\"']?\s*[:=]\s*[\"']?)[^\"'\s,]+", re.I), r"\1[REDACTED_PASSWORD]"),
    (re.compile(r"(client_secret[\"']?\s*[:=]\s*[\"']?)[^\"'\s,]+", re.I), r"\1[REDACTED_SECRET]"),
    (re.compile(r"(AIza[0-9A-Za-z\-_]{25,45})"), "[REDACTED_GEMINI_KEY]"),
    (re.compile(r"(AKIA[0-9A-Z]{16})"), "[REDACTED_AWS_KEY]"),
    (re.compile(r"([a-z]+://[^:]+:)[^@]+(@)", re.I), r"\1[REDACTED_CREDENTIALS]\2"),
]

ERROR_KEYWORDS = [
    "exception", "error", "fatal", "failed", "refused", "timeout",
    "panic", "cannot connect", "crash", "killed", "denied", "abort"
]


class LogCollector:
    def __init__(self, executor: Optional[KubectlExecutor] = None):
        self.executor = executor or kubectl_executor
        self.tail_lines = settings.KUBEVORA_LOG_TAIL

    @staticmethod
    def sanitize_logs(raw_text: str) -> str:
        """Redact sensitive credentials from log text."""
        sanitized = raw_text
        for pattern, replacement in REDACTION_PATTERNS:
            sanitized = pattern.sub(replacement, sanitized)
        return sanitized

    def collect_pod_logs(
        self,
        pod_name: str,
        namespace: str,
        container: Optional[str] = None,
        fetch_previous: bool = False,
    ) -> Dict[str, Any]:
        """Fetch logs for a single pod/container with optional previous crash logs."""
        args = ["logs", pod_name, "-n", namespace, f"--tail={self.tail_lines}"]
        if container:
            args.extend(["-c", container])
        if fetch_previous:
            args.append("--previous")

        res = self.executor.execute(args)
        if not res.success:
            return {
                "available": False,
                "error": res.error_message or "Logs unavailable",
                "lines": [],
            }

        sanitized = self.sanitize_logs(res.stdout)
        lines = [line.strip() for line in sanitized.splitlines() if line.strip()]

        # Extract lines matching error signals
        relevant_lines = [
            line for line in lines
            if any(kw in line.lower() for kw in ERROR_KEYWORDS)
        ][:15]

        return {
            "available": True,
            "total_lines": len(lines),
            "error_detected": len(relevant_lines) > 0,
            "relevant_lines": relevant_lines,
            "lines": lines[-50:],  # return the most recent 50 lines
        }

    def collect_logs_for_problematic_pods(
        self,
        problematic_pods: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """Collect logs for all detected problematic pods."""
        results = []
        for p in problematic_pods:
            pod_name = p.get("name")
            pod_ns = p.get("namespace")
            containers = p.get("containers", [])

            for c in containers:
                c_name = c.get("container")
                if c_name == "pod":
                    continue

                restarts = c.get("restart_count", 0)
                reason = c.get("reason", "")

                # 1. Fetch current logs
                curr = self.collect_pod_logs(pod_name, pod_ns, container=c_name, fetch_previous=False)
                if curr["available"]:
                    results.append({
                        "pod": pod_name,
                        "namespace": pod_ns,
                        "container": c_name,
                        "source": "current",
                        "error_detected": curr["error_detected"],
                        "relevant_lines": curr["relevant_lines"],
                        "sample_lines": curr["lines"][-20:],
                    })

                # 2. If restarted or crashed, fetch previous container logs
                if restarts > 0 or reason in ("CrashLoopBackOff", "OOMKilled", "Error"):
                    prev = self.collect_pod_logs(pod_name, pod_ns, container=c_name, fetch_previous=True)
                    if prev["available"]:
                        results.append({
                            "pod": pod_name,
                            "namespace": pod_ns,
                            "container": c_name,
                            "source": "previous",
                            "error_detected": prev["error_detected"],
                            "relevant_lines": prev["relevant_lines"],
                            "sample_lines": prev["lines"][-20:],
                        })

        return results