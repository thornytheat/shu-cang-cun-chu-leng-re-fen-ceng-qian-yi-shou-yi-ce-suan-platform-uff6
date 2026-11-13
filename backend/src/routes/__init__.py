"""路由总装配（统一 /api 前缀由 config/app.py 挂载）。"""
from fastapi import APIRouter

from src.routes import audit, auth, health, overview, plans, policies, tables

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(auth.router)
api_router.include_router(overview.router)
api_router.include_router(tables.router)
api_router.include_router(policies.router)
api_router.include_router(plans.router)
api_router.include_router(audit.router)

__all__ = ["api_router"]
