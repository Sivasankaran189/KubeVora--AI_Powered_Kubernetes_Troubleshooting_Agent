"""
Tests for Core API Endpoints (Health, Auth, Clusters, Investigations)
Invokes endpoint handlers directly with mock/isolated inputs using run_sync.
Runs deterministically and instantly without event loop socket blocks in Windows sandbox.
"""
import pytest
from app.main import root, health
from app.api.v1.health import liveness_probe, readiness_probe
from app.api.v1.auth import login
from app.api.v1.clusters import get_cluster_status, get_namespaces, get_workloads
from app.schemas.auth import UserLogin, UserResponse
from app.schemas.investigation import InvestigationCreate
from app.services.investigation_service import investigation_service


def run_sync(coro):
    """Executes a coroutine that completes immediately without external I/O loops."""
    try:
        coro.send(None)
    except StopIteration as e:
        return e.value
    raise RuntimeError("Coroutine did not complete synchronously")


@pytest.fixture
def test_user():
    return UserResponse(
        id="usr-test-sre-01",
        username="admin_sre",
        email="sre@kubevora.internal",
        full_name="Cluster Admin SRE",
        role="Site Reliability Engineer",
        is_active=True,
        permissions=["cluster:read", "cluster:investigate", "cluster:remediate"],
        created_at="2026-10-25T00:00:00Z"
    )


def test_root():
    resp = run_sync(root())
    # root returns a JSONResponse or dict
    if hasattr(resp, "body"):
        import json
        data = json.loads(resp.body.decode())
    else:
        data = resp
    assert data["app"] == "KubeVora"
    assert data["status"] == "operational"


def test_health_endpoint():
    data = run_sync(health())
    assert data["status"] == "healthy"
    assert data["service"] == "kubevora"


def test_health_probes():
    live_resp = run_sync(liveness_probe())
    assert live_resp.status == "alive"

    ready_resp = run_sync(readiness_probe())
    assert ready_resp.status == "ready"
    assert len(ready_resp.services) >= 3


def test_auth_and_protected_routes(test_user):
    # Test valid credentials for seeded admin
    login_in = UserLogin(
        username_or_email="admin_sre",
        password="adminpassword123"
    )
    token_resp = run_sync(login(login_in, db=None))
    assert token_resp.access_token is not None
    assert token_resp.token_type == "bearer"

    # Test invalid credentials raise 401
    bad_login = UserLogin(
        username_or_email="admin_sre",
        password="wrongpassword"
    )
    with pytest.raises(Exception):
        run_sync(login(bad_login, db=None))


def test_cluster_endpoints(test_user):
    status_data = run_sync(get_cluster_status(current_user=test_user))
    assert status_data.name in ("production-grid-primary", "gke-prod-primary-eu-west-1", "kind (kubevora-cluster)")
    assert status_data.nodes_ready >= 1

    namespaces = run_sync(get_namespaces(current_user=test_user))
    ns_names = [ns.name for ns in namespaces]
    assert "kube-system" in ns_names

    workloads = run_sync(get_workloads(namespace=None, current_user=test_user))
    assert len(workloads) > 0
    oom_workload = next((w for w in workloads if w.status == "CrashLoopBackOff"), None)
    assert oom_workload is not None


def test_investigations_and_pillars(test_user):
    invs = investigation_service.list_investigations()
    assert len(invs) >= 2

    inv_id = invs[0].id
    detail = investigation_service.get_investigation(inv_id)
    assert detail is not None
    assert detail.fingerprint.startswith("fp-k8s-")

    dispatch_payload = InvestigationCreate(
        title="Ingress Gateway HTTP 504 Gateway Timeout Spike",
        namespace="production",
        resource_kind="Deployment",
        resource_name="ingress-gateway",
        symptom="Upstream connection pool exhausted, repeated 504 status codes",
        severity="critical"
    )
    dispatched = investigation_service.dispatch_investigation(dispatch_payload)
    assert dispatched.title == dispatch_payload.title
    assert dispatched.has_fix_preview is True
