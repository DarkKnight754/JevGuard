from fastapi import APIRouter

from app.api.v1.routes import decisions

# Health lives at root (/health), not under /api/v1/
# It is registered directly in app/main.py
router = APIRouter(prefix="/api/v1")
router.include_router(decisions.router)
