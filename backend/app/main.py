from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.api import routes_agent, routes_system, ws_stream

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

# Attach API routers
app.include_router(routes_agent.router, prefix="/api/agent", tags=["Agent"])
app.include_router(routes_system.router, prefix="/api/system", tags=["System"])
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
