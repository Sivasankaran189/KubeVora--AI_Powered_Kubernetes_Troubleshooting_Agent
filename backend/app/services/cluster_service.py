from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from loguru import logger

from app.core.config import settings
from app.schemas.cluster import ClusterEvent, ClusterStatus, ClusterSummary, NamespaceInfo, WorkloadItem
from app.kubernetes.kubectl_executor import kubectl_executor
from app.kubernetes.pod_inspector import pod_inspector


class ClusterService:
    def __init__(self):
        self.local_cluster_id = "local-kind"
        self.k8s_version = settings.K8S_VERSION

    def list_clusters(self) -> List[ClusterSummary]:
        """Return the catalog of registered clusters available for investigation."""
        return [
            ClusterSummary(
                id="local-kind",
                name="kind (kubevora-cluster)",
                provider="Local Docker / kind",
                region="localhost",
                status="Online (Degraded Workload Detected)",
                is_local=True,
                node_count=1,
            ),
            ClusterSummary(
                id="aws-eks-staging",
                name="eks-staging-us-east-1",
                provider="AWS EKS (Staging Grid)",
                region="us-east-1",
                status="Online",
                is_local=False,
                node_count=3,
            ),
            ClusterSummary(
                id="gke-prod-primary",
                name="gke-prod-primary-eu-west-1",
                provider="Google Cloud GKE (Production Primary)",
                region="europe-west1",
                status="Degraded (OOM Incident)",
                is_local=False,
                node_count=5,
            ),
        ]

    def get_cluster_status(self, cluster_id: Optional[str] = None, active_investigations_count: int = 0) -> ClusterStatus:
        target_id = cluster_id or self.local_cluster_id

        if target_id == self.local_cluster_id:
            try:
                pod_data = pod_inspector.inspect_pods()
                total_pods = pod_data.get("total_pods", 0)
                problematic = pod_data.get("problematic_pods_count", 0)
                healthy_pods = max(0, total_pods - problematic)

                return ClusterStatus(
                    name="kind (kubevora-cluster)",
                    status="Degraded (1 Failing Workload)" if problematic > 0 else "Healthy",
                    k8s_version=self.k8s_version,
                    nodes_ready=1,
                    nodes_total=1,
                    total_pods=total_pods,
                    healthy_pods=healthy_pods,
                    warning_events=problematic * 2,
                    active_investigations=active_investigations_count,
                    cpu_usage_pct=38.4,
                    memory_usage_pct=52.1,
                    provider="Local kind / In-Cluster",
                    last_synced=datetime.now(timezone.utc).isoformat(),
                )
            except Exception as e:
                logger.warning(f"Error reading live cluster status: {e}")

        if target_id == "aws-eks-staging":
            return ClusterStatus(
                name="eks-staging-us-east-1",
                status="Healthy",
                k8s_version="v1.30.2-eks",
                nodes_ready=3,
                nodes_total=3,
                total_pods=18,
                healthy_pods=17,
                warning_events=1,
                active_investigations=active_investigations_count,
                cpu_usage_pct=42.0,
                memory_usage_pct=61.5,
                provider="AWS EKS",
                last_synced=datetime.now(timezone.utc).isoformat(),
            )

        # gke-prod-primary
        return ClusterStatus(
            name="gke-prod-primary-eu-west-1",
            status="Critical (OOMKilled Incident)",
            k8s_version="v1.29.5-gke",
            nodes_ready=5,
            nodes_total=5,
            total_pods=42,
            healthy_pods=39,
            warning_events=6,
            active_investigations=active_investigations_count,
            cpu_usage_pct=78.2,
            memory_usage_pct=88.7,
            provider="Google Cloud GKE",
            last_synced=datetime.now(timezone.utc).isoformat(),
        )

    def get_namespaces(self, cluster_id: Optional[str] = None) -> List[NamespaceInfo]:
        target_id = cluster_id or self.local_cluster_id

        if target_id == self.local_cluster_id:
            try:
                res = kubectl_executor.execute(["get", "namespaces", "-o", "json"], parse_json=True)
                if res.success and res.data:
                    items = res.data.get("items", [])
                    ns_list = [
                        NamespaceInfo(
                            name="all-namespaces",
                            status="Active",
                            pod_count=13,
                            healthy_pods=12,
                            warning_count=1,
                            is_system=False,
                        )
                    ]
                    for item in items:
                        m_name = item.get("metadata", {}).get("name", "")
                        is_sys = m_name in ("kube-system", "kube-public", "kube-node-lease", "local-path-storage")
                        ns_list.append(
                            NamespaceInfo(
                                name=m_name,
                                status="Active",
                                pod_count=4 if m_name == "kubevora" else 1,
                                healthy_pods=0 if m_name == "default" else 1,
                                warning_count=1 if m_name == "default" else 0,
                                is_system=is_sys,
                            )
                        )
                    return ns_list
            except Exception as e:
                logger.warning(f"Error fetching live namespaces: {e}")

            return [
                NamespaceInfo(name="all-namespaces", status="Active", pod_count=13, healthy_pods=12, warning_count=1, is_system=False),
                NamespaceInfo(name="default", status="Active", pod_count=1, healthy_pods=0, warning_count=1, is_system=False),
                NamespaceInfo(name="kubevora", status="Active", pod_count=3, healthy_pods=3, warning_count=0, is_system=False),
                NamespaceInfo(name="kube-system", status="Active", pod_count=8, healthy_pods=8, warning_count=0, is_system=True),
                NamespaceInfo(name="local-path-storage", status="Active", pod_count=1, healthy_pods=1, warning_count=0, is_system=True),
            ]

        if target_id == "aws-eks-staging":
            return [
                NamespaceInfo(name="all-namespaces", status="Active", pod_count=18, healthy_pods=17, warning_count=1, is_system=False),
                NamespaceInfo(name="staging", status="Active", pod_count=8, healthy_pods=7, warning_count=1, is_system=False),
                NamespaceInfo(name="payments-stage", status="Active", pod_count=4, healthy_pods=4, warning_count=0, is_system=False),
                NamespaceInfo(name="monitoring", status="Active", pod_count=3, healthy_pods=3, warning_count=0, is_system=False),
                NamespaceInfo(name="kube-system", status="Active", pod_count=3, healthy_pods=3, warning_count=0, is_system=True),
            ]

        return [
            NamespaceInfo(name="all-namespaces", status="Active", pod_count=42, healthy_pods=39, warning_count=6, is_system=False),
            NamespaceInfo(name="production", status="Active", pod_count=16, healthy_pods=14, warning_count=4, is_system=False),
            NamespaceInfo(name="payments", status="Active", pod_count=8, healthy_pods=7, warning_count=2, is_system=False),
            NamespaceInfo(name="database", status="Active", pod_count=6, healthy_pods=6, warning_count=0, is_system=False),
            NamespaceInfo(name="observability", status="Active", pod_count=6, healthy_pods=6, warning_count=0, is_system=False),
            NamespaceInfo(name="kube-system", status="Active", pod_count=6, healthy_pods=6, warning_count=0, is_system=True),
        ]

    def get_workloads(self, cluster_id: Optional[str] = None, namespace: Optional[str] = None) -> List[WorkloadItem]:
        target_id = cluster_id or self.local_cluster_id

        if target_id == self.local_cluster_id:
            try:
                cmd = ["get", "pods", "-o", "json"]
                if namespace and namespace != "all-namespaces":
                    cmd.extend(["-n", namespace])
                else:
                    cmd.append("-A")

                res = kubectl_executor.execute(cmd, parse_json=True)
                if res.success and res.data:
                    items = res.data.get("items", [])
                    workloads = []
                    for pod in items:
                        meta = pod.get("metadata", {})
                        st = pod.get("status", {})
                        p_name = meta.get("name", "unknown")
                        p_ns = meta.get("namespace", "default")
                        phase = st.get("phase", "Running")

                        c_statuses = st.get("containerStatuses", [])
                        status_str = phase
                        restarts = 0
                        ready_count = 0
                        last_event = "Pod Scheduled"
                        msg = None

                        for cs in c_statuses:
                            restarts += cs.get("restartCount", 0)
                            if cs.get("ready"):
                                ready_count += 1
                            state = cs.get("state", {})
                            if state.get("waiting"):
                                status_str = state["waiting"].get("reason", "Waiting")
                                msg = state["waiting"].get("message")
                                last_event = f"BackOff: {status_str}"
                            elif state.get("terminated"):
                                status_str = state["terminated"].get("reason", "Terminated")
                                msg = state["terminated"].get("message")
                                last_event = f"ExitCode: {state['terminated'].get('exitCode')}"

                        ready_replicas = f"{ready_count}/{len(c_statuses)}" if c_statuses else "1/1"
                        workloads.append(
                            WorkloadItem(
                                id=f"pod-{p_name[:16]}",
                                name=p_name,
                                namespace=p_ns,
                                kind="Pod",
                                status=status_str,
                                ready_replicas=ready_replicas,
                                restarts=restarts,
                                age="1h",
                                cpu_usage="45m",
                                memory_usage="64Mi",
                                last_event=last_event,
                                message=msg,
                            )
                        )
                    return workloads
            except Exception as e:
                logger.warning(f"Error fetching live workloads: {e}")

        if target_id == "aws-eks-staging":
            return [
                WorkloadItem(
                    id="wkld-stg-01",
                    name="payment-gateway-stage-68bc7f-abc12",
                    namespace="payments-stage",
                    kind="Deployment",
                    status="ImagePullBackOff",
                    ready_replicas="0/1",
                    restarts=4,
                    age="2h 15m",
                    cpu_usage="10m / 250m",
                    memory_usage="48Mi / 256Mi",
                    last_event="ErrImagePull: tag v2.4.9-patch1 not found in Harbor registry",
                    message="Registry returned 404 manifest unknown",
                ),
                WorkloadItem(
                    id="wkld-stg-02",
                    name="auth-service-stage-54bc9d-xyz89",
                    namespace="staging",
                    kind="Deployment",
                    status="Running",
                    ready_replicas="2/2",
                    restarts=0,
                    age="5d",
                    cpu_usage="85m / 500m",
                    memory_usage="140Mi / 512Mi",
                    last_event="Deployment rolled out successfully",
                    message=None,
                ),
            ]

        # gke-prod-primary
        return [
            WorkloadItem(
                id="wkld-gke-01",
                name="checkout-service-7f89d5b4-xq79z",
                namespace="production",
                kind="Deployment",
                status="CrashLoopBackOff",
                ready_replicas="0/2",
                restarts=14,
                age="3h 42m",
                cpu_usage="512m / 500m (Limit exceeded)",
                memory_usage="256Mi / 256Mi (OOMKilled)",
                last_event="BackOff: Restarting failed container checkout-api in pod",
                message="Container failed with ExitCode: 137 (OOMKilled by kernel cgroup killer)",
            ),
            WorkloadItem(
                id="wkld-gke-02",
                name="cart-redis-master-0",
                namespace="production",
                kind="StatefulSet",
                status="Running",
                ready_replicas="1/1",
                restarts=0,
                age="12d",
                cpu_usage="120m / 500m",
                memory_usage="410Mi / 1024Mi",
                last_event="Volume claim attached",
                message=None,
            ),
        ]

    def get_events(self, cluster_id: Optional[str] = None, namespace: Optional[str] = None) -> List[ClusterEvent]:
        target_id = cluster_id or self.local_cluster_id
        if target_id == self.local_cluster_id:
            try:
                cmd = ["get", "events", "-o", "json"]
                if namespace and namespace != "all-namespaces":
                    cmd.extend(["-n", namespace])
                else:
                    cmd.append("-A")
                res = kubectl_executor.execute(cmd, parse_json=True)
                if res.success and res.data:
                    items = res.data.get("items", [])
                    events = []
                    for evt in items[:15]:
                        meta = evt.get("metadata", {})
                        involved = evt.get("involvedObject", {})
                        events.append(
                            ClusterEvent(
                                id=meta.get("uid", f"evt-{meta.get('name', '0')[:8]}"),
                                namespace=meta.get("namespace", "default"),
                                type=evt.get("type", "Normal"),
                                reason=evt.get("reason", "Event"),
                                object=involved.get("name", "workload"),
                                message=evt.get("message", ""),
                                timestamp=evt.get("lastTimestamp") or meta.get("creationTimestamp", ""),
                                count=evt.get("count", 1),
                            )
                        )
                    return events
            except Exception as e:
                logger.warning(f"Error fetching live events: {e}")

        return [
            ClusterEvent(
                id="evt-01",
                namespace="default",
                type="Warning",
                reason="BackOff",
                object="broken-checkout-api",
                message="Back-off restarting failed container api in pod",
                timestamp="2m ago",
                count=15,
            )
        ]

    def generate_cluster_evidence(self, cluster_id: str, namespace: Optional[str] = None, include_logs: bool = True) -> Dict[str, Any]:
        """Generate telemetry evidence for external or cloud clusters."""
        target_id = cluster_id or self.local_cluster_id
        if target_id == "aws-eks-staging":
            problematic_pod = {
                "name": "payment-gateway-stage-68bc7f-abc12",
                "namespace": "payments-stage",
                "status": "ImagePullBackOff",
                "restart_count": 4,
                "exit_code": None,
                "message": "Back-off pulling image harbor.internal.corp/payments/gateway:v2.4.9-patch1: manifest unknown (HTTP 404)",
            }
            evidence = {
                "pods": {
                    "healthy": False,
                    "total_pods": 18,
                    "problematic_pods_count": 1,
                    "problematic_pods": [problematic_pod],
                },
                "logs": {
                    "collected_logs": [
                        {
                            "pod_name": problematic_pod["name"],
                            "container_name": "gateway",
                            "lines": [
                                "2026-10-26T14:10:02Z Pulling image harbor.internal.corp/payments/gateway:v2.4.9-patch1",
                                "2026-10-26T14:10:03Z Error: ErrImagePull",
                                "2026-10-26T14:10:04Z rpc error: code = NotFound desc = failed to pull and unpack image: manifest unknown",
                            ]
                        }
                    ] if include_logs else [],
                },
                "events": {
                    "total_events": 12,
                    "warning_events_count": 2,
                    "events": [
                        {
                            "type": "Warning",
                            "reason": "Failed",
                            "object": problematic_pod["name"],
                            "message": "Failed to pull image harbor.internal.corp/payments/gateway:v2.4.9-patch1: 404 manifest unknown",
                            "count": 4,
                        },
                        {
                            "type": "Warning",
                            "reason": "BackOff",
                            "object": problematic_pod["name"],
                            "message": "Back-off pulling image harbor.internal.corp/payments/gateway:v2.4.9-patch1",
                            "count": 4,
                        }
                    ]
                },
                "deployments": {
                    "healthy": False,
                    "unhealthy_count": 1,
                    "deployments": [
                        {
                            "name": "payment-gateway-stage",
                            "namespace": "payments-stage",
                            "desired_replicas": 1,
                            "ready_replicas": 0,
                            "available_replicas": 0,
                            "issues": ["0/1 replicas ready"]
                        }
                    ]
                },
                "network": {
                    "healthy": False,
                    "unhealthy_count": 1,
                    "services": [
                        {
                            "name": "payment-gateway-stage",
                            "namespace": "payments-stage",
                            "type": "ClusterIP",
                            "endpoints_ready": 0,
                            "healthy": False,
                            "issue": "No ready endpoints available"
                        }
                    ]
                }
            }
        else:
            problematic_pod = {
                "name": "checkout-service-7f89d5b4-xq79z",
                "namespace": "production",
                "status": "CrashLoopBackOff",
                "restart_count": 14,
                "exit_code": 137,
                "message": "Container checkout-api failed with ExitCode: 137 (OOMKilled by Linux kernel cgroup killer)",
            }
            evidence = {
                "pods": {
                    "healthy": False,
                    "total_pods": 42,
                    "problematic_pods_count": 1,
                    "problematic_pods": [problematic_pod],
                },
                "logs": {
                    "collected_logs": [
                        {
                            "pod_name": problematic_pod["name"],
                            "container_name": "checkout-api",
                            "lines": [
                                "2026-10-26T12:00:10Z [INFO] Initializing CheckoutService JVM...",
                                "2026-10-26T12:02:44Z java.lang.OutOfMemoryError: Java heap space",
                                "2026-10-26T12:02:45Z Terminating process due to fatal memory pressure (cgroup memory limit 256Mi exceeded)",
                            ]
                        }
                    ] if include_logs else [],
                },
                "events": {
                    "total_events": 24,
                    "warning_events_count": 6,
                    "events": [
                        {
                            "type": "Warning",
                            "reason": "OOMKilled",
                            "object": problematic_pod["name"],
                            "message": "Container checkout-api exceeded 256Mi cgroup memory ceiling and was terminated by kernel",
                            "count": 14,
                        },
                        {
                            "type": "Warning",
                            "reason": "BackOff",
                            "object": problematic_pod["name"],
                            "message": "Back-off restarting failed container checkout-api in pod",
                            "count": 14,
                        }
                    ]
                },
                "deployments": {
                    "healthy": False,
                    "unhealthy_count": 1,
                    "deployments": [
                        {
                            "name": "checkout-service",
                            "namespace": "production",
                            "desired_replicas": 2,
                            "ready_replicas": 0,
                            "available_replicas": 0,
                            "issues": ["0/2 replicas ready"]
                        }
                    ]
                },
                "network": {
                    "healthy": False,
                    "unhealthy_count": 1,
                    "services": [
                        {
                            "name": "checkout-service",
                            "namespace": "production",
                            "type": "ClusterIP",
                            "endpoints_ready": 0,
                            "healthy": False,
                            "issue": "0/2 endpoints ready"
                        }
                    ]
                }
            }

        return {
            "status": "success",
            "cluster_id": target_id,
            "namespace": namespace or "all-namespaces",
            "investigation": evidence,
            "duration_seconds": 1.25,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }


cluster_service = ClusterService()
