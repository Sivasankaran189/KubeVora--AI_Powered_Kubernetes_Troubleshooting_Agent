from fastapi import APIRouter

from app.api.v1.auth import router as auth_router
from app.api.v1.clusters import router as clusters_router
from app.api.v1.health import router as health_router
from app.api.v1.investigations import router as investigations_router

api_router = APIRouter()

api_router.include_router(health_router)
api_router.include_router(auth_router)
api_router.include_router(clusters_router)
api_router.include_router(investigations_router)
