import json
import time
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Any, Dict, Generator, Optional
from fastapi import FastAPI, Depends, Request, Response, status, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from loguru import logger

from app.api.v1.router import api_router
from app.core.config import settings
from app.core.logging import setup_logging
from app.core.security import decode_access_token
from app.db.dependencies import get_db
from app.db.session import SessionLocal, init_db
from app.services.k8s_investigation_service import k8s_investigation_service
from app.services.cluster_service import cluster_service
from app.ai.root_cause_analyzer import root_cause_analyzer
from app.services.persistence_service import persistence_service
from app.api.deps import get_current_user
from app.schemas.auth import UserResponse

# Initialize Loguru logger
logger = setup_logging()


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting KubeVora Backend Orchestrator...")
    logger.info(f"Environment: {settings.ENVIRONMENT} | API Prefix: {settings.API_V1_STR}")
    # Initialize DB tables if SQLite or local
    try:
        init_db()
        logger.info("Database initialized successfully.")
    except Exception as e:
        logger.warning(f"Database initialization notice: {e}")
    yield
    logger.info("Shutting down KubeVora Backend Orchestrator...")


app = FastAPI(
    title=settings.PROJECT_NAME,
    description="KubeVora: AI-Powered Kubernetes Troubleshooting Agent Backend",
    version=settings.VERSION,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    lifespan=lifespan,
)

# CORS Middleware setup
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount API v1 router
app.include_router(api_router, prefix=settings.API_V1_STR)


class InvestigationRequest(BaseModel):
    cluster_id: Optional[str] = Field("local-kind", description="Target Kubernetes cluster ID to investigate")
    namespace: Optional[str] = Field(None, description="Target Kubernetes namespace to investigate")
    include_logs: bool = Field(True, description="Whether to collect container logs for problematic pods")


def get_optional_user_id(request: Request) -> str:
    """Extract user_id from Bearer token if present, otherwise default to admin user."""
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header.split(" ", 1)[1].strip()
        payload = decode_access_token(token)
        if payload and payload.get("sub"):
            return str(payload.get("sub"))
    return "usr_sre_001"


@app.post("/investigate", tags=["Investigation"])
def run_cluster_investigation(
    payload: Optional[InvestigationRequest] = None,
    request: Request = None,
    db: Session = Depends(get_db),
):
    """
    On-demand Kubernetes cluster investigation endpoint with AI Root Cause Analysis & Persistence.
    Collects pods, logs, events, deployments, network, performs Gemini SRE analysis,
    and persists the investigation record in PostgreSQL.
    """
    req = payload or InvestigationRequest()
    target_cluster = req.cluster_id or "local-kind"
    target_ns = req.namespace or settings.KUBEVORA_DEFAULT_NAMESPACE
    user_id = get_optional_user_id(request) if request else "usr_sre_001"

    # 1. Create DB record in running state
    db_inv = None
    try:
        db_inv = persistence_service.create_investigation(
            db=db,
            user_id=user_id,
            cluster_context=target_cluster,
            namespace=target_ns,
        )
    except Exception as dbe:
        logger.warning(f"Could not initialize DB investigation record: {dbe}")

    # 2. Collect Evidence
    if target_cluster == "local-kind":
        investigation_result = k8s_investigation_service.run_investigation(
            namespace=target_ns,
            include_logs=req.include_logs
        )
    else:
        investigation_result = cluster_service.generate_cluster_evidence(
            cluster_id=target_cluster,
            namespace=target_ns,
            include_logs=req.include_logs
        )

    # 3. Perform AI SRE reasoning
    diagnosis = None
    if investigation_result.get("status") in ("success", "partial_failure"):
        diagnosis = root_cause_analyzer.analyze(investigation_result.get("investigation", {}))

    investigation_result["diagnosis"] = diagnosis

    # 4. Finalize persistence in DB
    if db_inv:
        try:
            persistence_service.record_findings(
                db=db,
                investigation_id=db_inv.id,
                evidence=investigation_result.get("investigation", {}),
            )
            fp_hash = persistence_service.record_or_update_fingerprint(
                db=db,
                user_id=user_id,
                namespace=target_ns,
                evidence=investigation_result.get("investigation", {}),
                diagnosis=diagnosis,
                investigation_id=db_inv.id,
            )
            inv_status = "completed" if investigation_result.get("status") == "success" else "partially_completed"
            persistence_service.finalize_investigation(
                db=db,
                investigation_id=db_inv.id,
                evidence=investigation_result.get("investigation", {}),
                diagnosis=diagnosis,
                duration_seconds=investigation_result.get("duration_seconds", 0.0),
                status=inv_status,
                fingerprint_hash=fp_hash,
            )
            investigation_result["investigation_id"] = db_inv.id
            investigation_result["fingerprint"] = fp_hash
        except Exception as pe:
            logger.error(f"Failed to persist investigation results: {pe}")

    return investigation_result


@app.post("/investigate/stream", tags=["Investigation"])
def stream_cluster_investigation(
    payload: Optional[InvestigationRequest] = None,
    request: Request = None,
):
    """
    Live investigation progress streaming via Server-Sent Events (SSE).
    Emits structured events as each actual stage starts and completes.
    """
    req = payload or InvestigationRequest()
    target_cluster = req.cluster_id or "local-kind"
    target_ns = req.namespace or settings.KUBEVORA_DEFAULT_NAMESPACE
    user_id = get_optional_user_id(request) if request else "usr_sre_001"

    def event_stream() -> Generator[str, None, None]:
        db = SessionLocal()
        inv_id = "inv_stream_init"
        t0 = time.perf_counter()
        evidence: Dict[str, Any] = {}
        errors = []

        try:
            # Stage 0: Started & DB record created
            try:
                db_inv = persistence_service.create_investigation(
                    db=db,
                    user_id=user_id,
                    cluster_context=target_cluster,
                    namespace=target_ns,
                )
                inv_id = db_inv.id
            except Exception as e:
                logger.warning(f"DB record creation in stream note: {e}")

            yield f"data: {json.dumps({'stage': 'started', 'status': 'running', 'investigation_id': inv_id, 'cluster_context': target_cluster, 'namespace': target_ns, 'message': f'Investigation started for cluster {target_cluster}'})}\n\n"

            if target_cluster == "local-kind":
                # Stage 1: Pods
                yield f"data: {json.dumps({'stage': 'pods', 'status': 'running', 'message': 'Inspecting pods & container states...'})}\n\n"
                try:
                    pod_res = k8s_investigation_service.pod_inspector.inspect_pods(target_ns)
                    evidence["pods"] = pod_res
                except Exception as e:
                    evidence["pods"] = {"error": str(e), "problematic_pods": []}
                    errors.append(f"Pods: {str(e)}")

                problematic_pods = evidence.get("pods", {}).get("problematic_pods", [])
                problematic_names = [p.get("name") for p in problematic_pods if p.get("name")]

                # Stage 2: Logs
                if req.include_logs:
                    yield f"data: {json.dumps({'stage': 'logs', 'status': 'running', 'message': f'Collecting logs for {len(problematic_pods)} problematic workload(s)...'})}\n\n"
                    try:
                        log_res = k8s_investigation_service.log_collector.collect_logs_for_problematic_pods(problematic_pods)
                        evidence["logs"] = {"collected_logs": log_res}
                    except Exception as e:
                        evidence["logs"] = {"collected_logs": [], "error": str(e)}
                        errors.append(f"Logs: {str(e)}")
                else:
                    evidence["logs"] = {"collected_logs": [], "skipped": True}

                # Stage 3: Events
                yield f"data: {json.dumps({'stage': 'events', 'status': 'running', 'message': 'Correlating Kubernetes warning events...'})}\n\n"
                try:
                    event_res = k8s_investigation_service.event_analyzer.analyze_events(target_ns, problematic_names)
                    evidence["events"] = event_res
                except Exception as e:
                    evidence["events"] = {"events": [], "error": str(e)}
                    errors.append(f"Events: {str(e)}")

                # Stage 4: Deployments
                yield f"data: {json.dumps({'stage': 'deployments', 'status': 'running', 'message': 'Checking deployment replicas & rollout status...'})}\n\n"
                try:
                    deploy_res = k8s_investigation_service.deployment_inspector.inspect_deployments(target_ns)
                    evidence["deployments"] = deploy_res
                except Exception as e:
                    evidence["deployments"] = {"deployments": [], "error": str(e)}
                    errors.append(f"Deployments: {str(e)}")

                # Stage 5: Network
                yield f"data: {json.dumps({'stage': 'network', 'status': 'running', 'message': 'Checking services & endpoint availability...'})}\n\n"
                try:
                    net_res = k8s_investigation_service.network_inspector.inspect_services(target_ns)
                    evidence["network"] = net_res
                except Exception as e:
                    evidence["network"] = {"services": [], "error": str(e)}
                    errors.append(f"Network: {str(e)}")
            else:
                # Simulated remote / cloud cluster telemetry
                cluster_ev = cluster_service.generate_cluster_evidence(target_cluster, target_ns, req.include_logs)
                full_ev = cluster_ev.get("investigation", {})
                time.sleep(0.3)
                yield f"data: {json.dumps({'stage': 'pods', 'status': 'running', 'message': f'Inspecting remote pods & container states in {target_cluster}...'})}\n\n"
                evidence["pods"] = full_ev.get("pods", {})
                time.sleep(0.3)
                yield f"data: {json.dumps({'stage': 'logs', 'status': 'running', 'message': f'Collecting remote workload logs in {target_cluster}...'})}\n\n"
                evidence["logs"] = full_ev.get("logs", {})
                time.sleep(0.3)
                yield f"data: {json.dumps({'stage': 'events', 'status': 'running', 'message': f'Correlating cluster warning events in {target_cluster}...'})}\n\n"
                evidence["events"] = full_ev.get("events", {})
                time.sleep(0.3)
                yield f"data: {json.dumps({'stage': 'deployments', 'status': 'running', 'message': f'Checking deployment replicas in {target_cluster}...'})}\n\n"
                evidence["deployments"] = full_ev.get("deployments", {})
                time.sleep(0.3)
                yield f"data: {json.dumps({'stage': 'network', 'status': 'running', 'message': f'Checking services & endpoints in {target_cluster}...'})}\n\n"
                evidence["network"] = full_ev.get("network", {})

            # Stage 6: AI Reasoning with Gemini
            yield f"data: {json.dumps({'stage': 'ai_reasoning', 'status': 'running', 'message': 'Running Senior SRE reasoning with Google Gemini...'})}\n\n"
            diagnosis = root_cause_analyzer.analyze(evidence)

            # Stage 7: Persisting findings
            yield f"data: {json.dumps({'stage': 'persisting', 'status': 'running', 'message': 'Persisting investigation report & incident fingerprint...'})}\n\n"
            elapsed = round(time.perf_counter() - t0, 3)
            fp_hash = None

            try:
                persistence_service.record_findings(db=db, investigation_id=inv_id, evidence=evidence)
                fp_hash = persistence_service.record_or_update_fingerprint(
                    db=db,
                    user_id=user_id,
                    namespace=target_ns,
                    evidence=evidence,
                    diagnosis=diagnosis,
                    investigation_id=inv_id,
                )
                final_status = "completed" if not errors else "partially_completed"
                persistence_service.finalize_investigation(
                    db=db,
                    investigation_id=inv_id,
                    evidence=evidence,
                    diagnosis=diagnosis,
                    duration_seconds=elapsed,
                    status=final_status,
                    fingerprint_hash=fp_hash,
                )
            except Exception as pe:
                logger.error(f"Persistence error during stream: {pe}")

            # Stage 8: Completed
            completed_payload = {
                "stage": "completed",
                "status": "completed" if not errors else "partially_completed",
                "investigation_id": inv_id,
                "cluster_context": target_cluster,
                "namespace": target_ns,
                "duration_seconds": elapsed,
                "fingerprint": fp_hash,
                "investigation": evidence,
                "diagnosis": diagnosis,
                "errors": errors,
            }
            yield f"data: {json.dumps(completed_payload)}\n\n"

        except Exception as ex:
            logger.error(f"Fatal error during investigation streaming: {ex}")
            yield f"data: {json.dumps({'stage': 'failed', 'status': 'failed', 'investigation_id': inv_id, 'error': str(ex)})}\n\n"
        finally:
            db.close()

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        }
    )


# Root alias routes for direct frontend endpoints
@app.get("/investigations", tags=["Root Investigations Alias"])
async def root_list_investigations(
    cluster_id: Optional[str] = None,
    namespace: Optional[str] = None,
    limit: int = 50,
    current_user: UserResponse = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    from app.api.v1.investigations import list_investigations as v1_list
    return await v1_list(cluster_id=cluster_id, namespace=namespace, limit=limit, current_user=current_user, db=db)


@app.get("/investigations/{investigation_id}", tags=["Root Investigations Alias"])
async def root_get_investigation(
    investigation_id: str,
    current_user: UserResponse = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    from app.api.v1.investigations import get_investigation as v1_get
    return await v1_get(investigation_id=investigation_id, current_user=current_user, db=db)


@app.get("/health", tags=["Health"])
async def health():
    """
    Core health check endpoint.
    Returns:
        {"status": "healthy", "service": "kubevora"}
    """
    return {
        "status": "healthy",
        "service": "kubevora",
    }


@app.get("/", tags=["Root"])
async def root():
    return JSONResponse(
        content={
            "app": settings.PROJECT_NAME,
            "tagline": settings.TAGLINE,
            "version": settings.VERSION,
            "status": "operational",
            "docs": "/docs",
            "api_prefix": settings.API_V1_STR,
            "health": "/health",
            "probes": {
                "liveness": f"{settings.API_V1_STR}/health/live",
                "readiness": f"{settings.API_V1_STR}/health/ready",
            },
        }
    )
