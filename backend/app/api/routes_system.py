from fastapi import APIRouter
from app.core.tools import get_system_stats
from app.config import settings

router = APIRouter()

@router.get("/stats")
async def system_stats_endpoint():
    stats = get_system_stats()
    return {"status": "success", "data": stats}

@router.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "assistant_name": settings.ASSISTANT_NAME,
        "version": settings.APP_VERSION,
        "gemini_configured": bool(settings.GEMINI_API_KEY)
    }
