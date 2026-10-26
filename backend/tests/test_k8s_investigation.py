"""
Unit tests for Kubernetes Investigation Layer (Prompt 2).
All subprocess calls to kubectl are mocked, allowing tests to run completely offline.
"""
import json
import pytest
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient

from app.main import app
from app.kubernetes.kubectl_executor import KubectlExecutor, KubectlResult
from app.kubernetes.pod_inspector import PodInspector
from app.kubernetes.log_collector import LogCollector
from app.kubernetes.event_analyzer import EventsAnalyzer
from app.kubernetes.deployment_inspector import DeploymentInspector
from app.kubernetes.network_inspector import NetworkInspector
from app.services.k8s_investigation_service import K8sInvestigationService


# ---------------------------------------------------------------------------
# 1. KubectlExecutor Tests
# ---------------------------------------------------------------------------

def test_kubectl_name_validation():
    executor = KubectlExecutor()
    assert executor.validate_name("default") is True
    assert executor.validate_name("kube-system") is True
    assert executor.validate_name("my-pod-123.test") is True
    assert executor.validate_name("Invalid_Name!") is False
    assert executor.validate_name("rm -rf /") is False
    assert executor.validate_name("") is False


@patch("shutil.which")
@patch("subprocess.run")
def test_kubectl_executor_success(mock_run, mock_which):
    mock_which.return_value = "/usr/bin/kubectl"
    mock_process = MagicMock()
    mock_process.returncode = 0
    mock_process.stdout = '{"status": "ok"}'
    mock_process.stderr = ""
    mock_run.return_value = mock_process

    executor = KubectlExecutor()
    res = executor.execute(["get", "pods", "-o", "json"], parse_json=True)
    assert res.success is True
    assert res.returncode == 0
    assert res.data == {"status": "ok"}
    assert res.error_message is None


@patch("shutil.which")
def test_kubectl_executor_missing_binary(mock_which):
    mock_which.return_value = None
    executor = KubectlExecutor()
    res = executor.execute(["get", "pods"])
    assert res.success is False
    assert res.returncode == -1
    assert "not found in PATH" in res.stderr


@patch("shutil.which")
@patch("subprocess.run")
def test_kubectl_executor_timeout(mock_run, mock_which):
    import subprocess
    mock_which.return_value = "/usr/bin/kubectl"
    mock_run.side_effect = subprocess.TimeoutExpired(cmd=["kubectl"], timeout=5)

    executor = KubectlExecutor(default_timeout=5)
    res = executor.execute(["get", "pods"])
    assert res.success is False
    assert res.returncode == -1
    assert "timed out" in res.stderr.lower()


# ---------------------------------------------------------------------------
# 2. PodInspector Tests
# ---------------------------------------------------------------------------

def test_pod_inspector_detects_crashloop_and_oom():
    sample_pods_json = {
        "items": [
            # 1. CrashLoopBackOff pod
            {
                "metadata": {"name": "crashed-app", "namespace": "default"},
                "status": {
                    "phase": "Running",
                    "containerStatuses": [
                        {
                            "name": "worker",
                            "restartCount": 5,
                            "state": {
                                "waiting": {
                                    "reason": "CrashLoopBackOff",
                                    "message": "back-off 5m restarting failed container"
                                }
                            }
                        }
                    ]
                }
            },
            # 2. OOMKilled pod
            {
                "metadata": {"name": "oom-app", "namespace": "default"},
                "status": {
                    "phase": "Running",
                    "containerStatuses": [
                        {
                            "name": "api",
                            "restartCount": 2,
                            "state": {
                                "terminated": {
                                    "reason": "OOMKilled",
                                    "exitCode": 137,
                                    "message": "Container exceeded memory limit"
                                }
                            }
                        }
                    ]
                }
            },
            # 3. Healthy pod
            {
                "metadata": {"name": "healthy-app", "namespace": "default"},
                "status": {
                    "phase": "Running",
                    "containerStatuses": [
                        {
                            "name": "web",
                            "restartCount": 0,
                            "state": {"running": {}}
                        }
                    ]
                }
            }
        ]
    }

    mock_executor = MagicMock()
    mock_executor.validate_name.return_value = True
    mock_executor.execute.return_value = KubectlResult(
        success=True,
        returncode=0,
        stdout=json.dumps(sample_pods_json),
        stderr="",
        data=sample_pods_json
    )

    inspector = PodInspector(executor=mock_executor)
    report = inspector.inspect_pods("default")

    assert report["healthy"] is False
    assert report["total_pods"] == 3
    assert report["problematic_pods_count"] == 2

    reasons = [p["status"] for p in report["problematic_pods"]]
    assert "CrashLoopBackOff" in reasons
    assert "OOMKilled" in reasons


# ---------------------------------------------------------------------------
# 3. LogCollector Tests (Redaction & Previous Logs)
# ---------------------------------------------------------------------------

def test_log_sanitizer_redacts_credentials():
    collector = LogCollector()
    raw = (
        "Connecting with Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.e30.fake_jwt_token\n"
        "Failed connection to postgres://admin:superSecretPass123@db.prod:5432/main\n"
        "Config key: password='mypassword123'\n"
        "Google API key AIzaSyD9876543210AbCdEfGhIjKlMnOpQrStU"
    )

    sanitized = collector.sanitize_logs(raw)
    assert "superSecretPass123" not in sanitized
    assert "[REDACTED_PASSWORD]" in sanitized
    assert "[REDACTED_JWT]" in sanitized
    assert "[REDACTED_GEMINI_KEY]" in sanitized


def test_log_collector_fetches_previous_on_crash():
    mock_executor = MagicMock()
    mock_executor.execute.return_value = KubectlResult(
        success=True,
        returncode=0,
        stdout="[FATAL] Panic in goroutine: nil pointer dereference\nexit status 2",
        stderr=""
    )

    collector = LogCollector(executor=mock_executor)
    problematic = [
        {
            "name": "crashed-app",
            "namespace": "default",
            "containers": [
                {
                    "container": "worker",
                    "restart_count": 3,
                    "reason": "CrashLoopBackOff"
                }
            ]
        }
    ]

    logs = collector.collect_logs_for_problematic_pods(problematic)
    assert len(logs) == 2  # Current + Previous
    sources = [l["source"] for l in logs]
    assert "current" in sources
    assert "previous" in sources
    assert any("Panic in goroutine" in l["relevant_lines"][0] for l in logs if l["relevant_lines"])


# ---------------------------------------------------------------------------
# 4. EventsAnalyzer Tests
# ---------------------------------------------------------------------------

def test_events_analyzer_prioritizes_warnings():
    sample_events = {
        "items": [
            {
                "type": "Warning",
                "reason": "BackOff",
                "message": "Back-off restarting failed container",
                "involvedObject": {"kind": "Pod", "name": "crashed-app", "namespace": "default"},
                "count": 12,
            },
            {
                "type": "Normal",
                "reason": "Scheduled",
                "message": "Successfully assigned default/healthy-app to node-1",
                "involvedObject": {"kind": "Pod", "name": "healthy-app", "namespace": "default"},
                "count": 1,
            }
        ]
    }

    mock_executor = MagicMock()
    mock_executor.execute.return_value = KubectlResult(
        success=True, returncode=0, stdout="", stderr="", data=sample_events
    )

    analyzer = EventsAnalyzer(executor=mock_executor)
    res = analyzer.analyze_events("default", involved_pod_names=["crashed-app"])

    assert res["total_events"] == 2
    assert res["warning_events_count"] == 1
    assert len(res["events"]) == 1
    assert res["events"][0]["reason"] == "BackOff"


# ---------------------------------------------------------------------------
# 5. DeploymentInspector Tests
# ---------------------------------------------------------------------------

def test_deployment_inspector_scaled_to_zero_not_unhealthy():
    sample_deploys = {
        "items": [
            # Deliberately scaled to 0
            {
                "metadata": {"name": "batch-worker", "namespace": "default"},
                "spec": {"replicas": 0},
                "status": {"readyReplicas": 0, "availableReplicas": 0}
            },
            # Broken deployment (1 desired, 0 ready)
            {
                "metadata": {"name": "broken-web", "namespace": "default"},
                "spec": {"replicas": 2},
                "status": {
                    "readyReplicas": 0,
                    "availableReplicas": 0,
                    "conditions": [{"type": "Progressing", "reason": "ProgressDeadlineExceeded"}]
                }
            }
        ]
    }

    mock_executor = MagicMock()
    mock_executor.execute.return_value = KubectlResult(
        success=True, returncode=0, stdout="", stderr="", data=sample_deploys
    )

    inspector = DeploymentInspector(executor=mock_executor)
    res = inspector.inspect_deployments("default")

    assert res["healthy"] is False
    assert res["unhealthy_count"] == 1
    assert res["deployments"][0]["name"] == "batch-worker"
    assert res["deployments"][0]["healthy"] is True  # Scaled to 0 is healthy!
    assert res["deployments"][1]["name"] == "broken-web"
    assert res["deployments"][1]["healthy"] is False


# ---------------------------------------------------------------------------
# 6. NetworkInspector Tests
# ---------------------------------------------------------------------------

def test_network_inspector_selector_no_endpoints():
    sample_services = {
        "items": [
            {
                "metadata": {"name": "web-svc", "namespace": "default"},
                "spec": {"type": "ClusterIP", "selector": {"app": "web"}},
            }
        ]
    }
    sample_endpoints = {"items": []}  # No endpoints for web-svc

    mock_executor = MagicMock()
    mock_executor.execute.side_effect = [
        KubectlResult(success=True, returncode=0, stdout="", stderr="", data=sample_services),
        KubectlResult(success=True, returncode=0, stdout="", stderr="", data=sample_endpoints),
    ]

    inspector = NetworkInspector(executor=mock_executor)
    res = inspector.inspect_services("default")

    assert res["healthy"] is False
    assert res["unhealthy_count"] == 1
    assert "0 ready endpoints" in res["services"][0]["issues"][0]


# ---------------------------------------------------------------------------
# 7. POST /investigate API Test
# ---------------------------------------------------------------------------

@patch("app.main.k8s_investigation_service.run_investigation")
def test_investigate_endpoint(mock_run):
    mock_run.return_value = {
        "status": "success",
        "cluster_context": "test-context",
        "namespace": "default",
        "started_at": "2026-10-25T10:00:00Z",
        "completed_at": "2026-10-25T10:00:01Z",
        "duration_seconds": 1.0,
        "investigation": {
            "pods": {"healthy": True},
            "logs": {"collected_logs": []},
            "events": {"events": []},
            "deployments": {"healthy": True},
            "network": {"healthy": True}
        },
        "component_status": {
            "pods": "success",
            "logs": "success",
            "events": "success",
            "deployments": "success",
            "network": "success"
        },
        "errors": []
    }

    from app.main import run_cluster_investigation, InvestigationRequest

    req = InvestigationRequest(namespace="default", include_logs=True)
    data = run_cluster_investigation(req)
    assert data["status"] == "success"
    assert "investigation" in data
    assert "component_status" in data
    assert data["component_status"]["pods"] == "success"
