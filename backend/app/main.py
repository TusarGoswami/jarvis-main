import logging
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.core.logging_config import setup_logging
from app.core.sanitizer import sanitize_text
from app.api import routes_agent, routes_system, routes_workspace, routes_interview, ws_stream, routes_auth

# Initialize structured logging
setup_logging()
logger = logging.getLogger("vocalis.api")

app = FastAPI(
    title="Vocalis AI",
    version=settings.APP_VERSION,
    description="Multimodal Voice & Vision Agentic Operating System"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def on_startup():
    try:
        from engine.db import init_db
        from app.core.reminder_service import get_scheduler
        init_db()
        get_scheduler()
        logger.info("Vocalis AI database & persistent reminder scheduler initialized.")
    except Exception as e:
        logger.error(f"Startup initialization error: {e}")

# Global unhandled exception handler (B2 Error Tracking)
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    sanitized_err = sanitize_text(str(exc))
    logger.error(
        f"Unhandled error on {request.method} {request.url.path}: {sanitized_err}",
        exc_info=True,
        extra={"path": request.url.path, "method": request.method}
    )
    return JSONResponse(
        status_code=500,
        content={
            "status": "error",
            "message": "An internal server error occurred. Please check system logs.",
            "detail": sanitized_err
        }
    )

# Attach API routers
app.include_router(routes_auth.router, tags=["Authentication"])
app.include_router(routes_agent.router, prefix="/api/agent", tags=["Agent"])
app.include_router(routes_system.router, prefix="/api/system", tags=["System"])
app.include_router(routes_workspace.router, tags=["Workspace"])
app.include_router(routes_interview.router, tags=["Interview Protocol"])
app.include_router(ws_stream.router, prefix="/ws", tags=["WebSocket"])

@app.get("/")
async def root():
    return {
        "service": "Vocalis AI Engine",
        "status": "online",
        "version": settings.APP_VERSION,
        "endpoints": {
            "docs": "/docs",
            "system_stats": "/api/system/stats",
            "agent_command": "/api/agent/command",
            "websocket_stream": "/ws/stream"
        }
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host=settings.HOST, port=settings.PORT, reload=settings.DEBUG)

