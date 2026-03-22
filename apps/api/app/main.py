from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import auth, bracelet, devices, patterns, seed, sessions, simulate, summaries
from app.core.config import settings

app = FastAPI(title=settings.app_name)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.allow_cors_origin],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(devices.router)
app.include_router(bracelet.router)
app.include_router(sessions.router)
app.include_router(summaries.router)
app.include_router(patterns.router)
app.include_router(simulate.router)
app.include_router(seed.router)


@app.get("/")
def root() -> dict[str, object]:
    return {
        "name": settings.app_name,
        "mode": "mock-first",
        "hardware_ready": True,
        "hardware_required_now": False,
    }
