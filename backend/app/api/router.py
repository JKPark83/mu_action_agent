from fastapi import APIRouter

from app.api.v1 import analyses, files, health
from app.api.websocket import analyses as ws_analyses

api_router = APIRouter()

api_router.include_router(health.router, tags=["health"])
api_router.include_router(analyses.router, prefix="/analyses", tags=["analyses"])
api_router.include_router(files.router, prefix="/files", tags=["files"])
api_router.include_router(ws_analyses.router, tags=["websocket"])
