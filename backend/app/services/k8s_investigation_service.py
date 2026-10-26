"""
KubeVora - Investigation Service Orchestrator
Coordinates read-only telemetry collectors to assemble an investigation evidence payload.
"""
from datetime import datetime, timezone
import time
from typing import Any, Dict, List, Optional
from loguru import logger
from app.core.config import settings
from app.kubernetes.pod_inspector import PodInspector
from app.kubernetes.log_collector import LogCollector
from app.kubernetes.event_analyzer import EventsAnalyzer
from app.kubernetes.deployment_inspector import DeploymentInspector
from app.kubernetes.network_inspector import NetworkInspector


class K8sInvestigationService:
    def __init__(self):
        self.pod_inspector = PodInspector()
        self.log_collector = LogCollector()
        self.event_analyzer = EventsAnalyzer()
        self.deployment_inspector = DeploymentInspector()
        self.network_inspector = NetworkInspector()

    def run_investigation(
        self,
        namespace: Optional[str] = None,
        include_logs: bool = True,
    ) -> Dict[str, Any]:
        """Execute full evidence gathering pipeline."""
        target_ns = namespace or settings.KUBEVORA_DEFAULT_NAMESPACE
        start_time_iso = datetime.now(timezone.utc).isoformat()
        t0 = time.perf_counter()

        evidence = {}
        component_status = {}
        errors = []

        # 1. Pods
        try:
            pod_results = self.pod_inspector.inspect_pods(target_ns)
            evidence["pods"] = pod_results
            component_status["pods"] = "success"
        except Exception as e:
            logger.error(f"PodInspector error: {e}")
            evidence["pods"] = {"error": str(e), "problematic_pods": []}
            component_status["pods"] = "failed"
            errors.append(f"PodInspector: {str(e)}")

        problematic_pods = evidence.get("pods", {}).get("problematic_pods", [])
        problematic_names = [p.get("name") for p in problematic_pods if p.get("name")]

        # 2. Logs
        if include_logs:
            try:
                log_results = self.log_collector.collect_logs_for_problematic_pods(problematic_pods)
                evidence["logs"] = {"collected_logs": log_results}
                component_status["logs"] = "success"
            except Exception as e:
                logger.error(f"LogCollector error: {e}")
                evidence["logs"] = {"collected_logs": [], "error": str(e)}
                component_status["logs"] = "failed"
                errors.append(f"LogCollector: {str(e)}")
        else:
            evidence["logs"] = {"collected_logs": [], "skipped": True}
            component_status["logs"] = "skipped"

        # 3. Events
        try:
            event_results = self.event_analyzer.analyze_events(target_ns, problematic_names)
            evidence["events"] = event_results
            component_status["events"] = "success"
        except Exception as e:
            logger.error(f"EventsAnalyzer error: {e}")
            evidence["events"] = {"events": [], "error": str(e)}
            component_status["events"] = "failed"
            errors.append(f"EventsAnalyzer: {str(e)}")

        # 4. Deployments
        try:
            deploy_results = self.deployment_inspector.inspect_deployments(target_ns)
            evidence["deployments"] = deploy_results
            component_status["deployments"] = "success"
        except Exception as e:
            logger.error(f"DeploymentInspector error: {e}")
            evidence["deployments"] = {"deployments": [], "error": str(e)}
            component_status["deployments"] = "failed"
            errors.append(f"DeploymentInspector: {str(e)}")

        # 5. Network
        try:
            net_results = self.network_inspector.inspect_services(target_ns)
            evidence["network"] = net_results
            component_status["network"] = "success"
        except Exception as e:
            logger.error(f"NetworkInspector error: {e}")
            evidence["network"] = {"services": [], "error": str(e)}
            component_status["network"] = "failed"
            errors.append(f"NetworkInspector: {str(e)}")

        elapsed = round(time.perf_counter() - t0, 3)
        end_time_iso = datetime.now(timezone.utc).isoformat()

        overall_status = "success" if not errors else ("partial_failure" if len(errors) < 5 else "failed")

        return {
            "status": overall_status,
            "cluster_context": settings.KUBERNETES_CONTEXT or "default",
            "namespace": target_ns,
            "started_at": start_time_iso,
            "completed_at": end_time_iso,
            "duration_seconds": elapsed,
            "investigation": evidence,
            "component_status": component_status,
            "errors": errors,
        }


k8s_investigation_service = K8sInvestigationService()