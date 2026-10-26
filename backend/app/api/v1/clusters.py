from typing import List, Optional
from fastapi import APIRouter, Depends, Query, status

from app.api.deps import get_current_user
from app.schemas.auth import UserResponse
from app.schemas.cluster import ClusterEvent, ClusterStatus, ClusterSummary, NamespaceInfo, WorkloadItem
from app.services.cluster_service import cluster_service
from app.services.investigation_service import investigation_service

router = APIRouter(prefix="/clusters", tags=["Cluster & Workload Telemetry"])


@router.get(
    "/list",
    response_model=List[ClusterSummary],
    status_code=status.HTTP_200_OK,
    summary="List all registered Kubernetes clusters (local and external)"
)
async def list_clusters(
    current_user: UserResponse = Depends(get_current_user)
) -> List[ClusterSummary]:
    """
    Returns the fleet of Kubernetes clusters available to the authenticated SRE.
    """
    return cluster_service.list_clusters()


@router.get(
    "/status",
    response_model=ClusterStatus,
    status_code=status.HTTP_200_OK,
    summary="Get current cluster status and resource health"
)
async def get_cluster_status(
    cluster_id: Optional[str] = Query(None, description="Target cluster ID"),
    current_user: UserResponse = Depends(get_current_user)
) -> ClusterStatus:
    """
    Returns aggregate cluster health, node statuses, pod counts, and resource gauges.
    """
    active_invs = len(investigation_service.list_investigations())
    return cluster_service.get_cluster_status(
        cluster_id=cluster_id,
        active_investigations_count=active_invs
    )


@router.get(
    "/namespaces",
    response_model=List[NamespaceInfo],
    status_code=status.HTTP_200_OK,
    summary="List cluster namespaces and health counts"
)
async def get_namespaces(
    cluster_id: Optional[str] = Query(None, description="Target cluster ID"),
    current_user: UserResponse = Depends(get_current_user)
) -> List[NamespaceInfo]:
    """
    Returns namespace catalog with pod health counts.
    """
    return cluster_service.get_namespaces(cluster_id=cluster_id)


@router.get(
    "/workloads",
    response_model=List[WorkloadItem],
    status_code=status.HTTP_200_OK,
    summary="List cluster workloads with live status"
)
async def get_workloads(
    cluster_id: Optional[str] = Query(None, description="Target cluster ID"),
    namespace: Optional[str] = Query(None, description="Filter workloads by namespace"),
    current_user: UserResponse = Depends(get_current_user)
) -> List[WorkloadItem]:
    """
    Returns list of workloads (Deployments, Pods, StatefulSets) with live status.
    """
    return cluster_service.get_workloads(cluster_id=cluster_id, namespace=namespace)


@router.get(
    "/events",
    response_model=List[ClusterEvent],
    status_code=status.HTTP_200_OK,
    summary="List cluster warning and error events"
)
async def get_events(
    cluster_id: Optional[str] = Query(None, description="Target cluster ID"),
    namespace: Optional[str] = Query(None, description="Filter events by namespace"),
    current_user: UserResponse = Depends(get_current_user)
) -> List[ClusterEvent]:
    """
    Returns active Kubernetes warning/error events for correlation.
    """
    return cluster_service.get_events(cluster_id=cluster_id, namespace=namespace)
