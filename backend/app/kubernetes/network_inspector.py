"""
KubeVora - Network Inspector
Inspects Services and Endpoints for selector mismatches and missing backends.
"""
from typing import Any, Dict, List, Optional
from app.kubernetes.kubectl_executor import KubectlExecutor, kubectl_executor


class NetworkInspector:
    def __init__(self, executor: Optional[KubectlExecutor] = None):
        self.executor = executor or kubectl_executor

    def inspect_services(self, namespace: Optional[str] = None) -> Dict[str, Any]:
        # 1. Fetch Services
        svc_args = ["get", "services", "-o", "json"]
        if namespace and namespace != "all-namespaces":
            svc_args.extend(["-n", namespace])
        else:
            svc_args.append("-A")
        svc_res = self.executor.execute(svc_args, parse_json=True)

        # 2. Fetch Endpoints
        ep_args = ["get", "endpoints", "-o", "json"]
        if namespace and namespace != "all-namespaces":
            ep_args.extend(["-n", namespace])
        else:
            ep_args.append("-A")
        ep_res = self.executor.execute(ep_args, parse_json=True)

        if not svc_res.success:
            return {"healthy": False, "error": svc_res.error_message, "services": []}

        # Map endpoints by "namespace/name"
        endpoints_map = {}
        if ep_res.success and ep_res.data:
            for ep in ep_res.data.get("items", []):
                ep_ns = ep.get("metadata", {}).get("namespace", "default")
                ep_name = ep.get("metadata", {}).get("name", "")
                subsets = ep.get("subsets", [])
                ready_addresses = 0
                for sub in subsets:
                    ready_addresses += len(sub.get("addresses", []))
                endpoints_map[f"{ep_ns}/{ep_name}"] = ready_addresses

        services = []
        unhealthy_count = 0

        for svc in (svc_res.data or {}).get("items", []):
            name = svc.get("metadata", {}).get("name", "")
            ns = svc.get("metadata", {}).get("namespace", "default")
            spec = svc.get("spec", {})
            svc_type = spec.get("type", "ClusterIP")
            selector = spec.get("selector", {})

            # Headless or external services have no selectors
            is_headless = spec.get("clusterIP") == "None"
            has_selector = bool(selector)

            issues = []
            ready_endpoints = endpoints_map.get(f"{ns}/{name}", 0)

            # If service has selectors but zero ready endpoints, flag it
            if has_selector and ready_endpoints == 0:
                issues.append("Service has selectors configured but 0 ready endpoints")

            is_healthy = len(issues) == 0
            if not is_healthy:
                unhealthy_count += 1

            services.append({
                "name": name,
                "namespace": ns,
                "type": svc_type,
                "healthy": is_healthy,
                "has_selector": has_selector,
                "selector": selector,
                "ready_endpoints": ready_endpoints,
                "issues": issues,
            })

        return {
            "healthy": unhealthy_count == 0,
            "total_services": len(services),
            "unhealthy_count": unhealthy_count,
            "services": services,
        }