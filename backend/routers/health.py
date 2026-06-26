"""Health and LLM status endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Request

from database import get_database
from llm.router import get_llm_router
from models import HealthResponse, LLMStatusResponse
from utils.proxy_pool import get_pool_stats

router = APIRouter(tags=["health"])

_DEFAULT_LLM = {
    "provider": "none",
    "model": "none",
    "latency_ms": None,
    "available_providers": [],
}


@router.get("/health", response_model=HealthResponse)
async def health_check(request: Request) -> HealthResponse:
    db_status = "ok"
    try:
        db = await get_database()
        await db.conn.execute("SELECT 1")
    except Exception:
        db_status = "error"

    llm_status = getattr(request.app.state, "llm_status", _DEFAULT_LLM)
    llm_name = llm_status.get("provider", "unknown")

    return HealthResponse(
        status="ok" if db_status == "ok" else "degraded",
        db=db_status,
        llm=llm_name,
    )


@router.get("/llm/status", response_model=LLMStatusResponse)
async def llm_status(request: Request) -> LLMStatusResponse:
    cached = getattr(request.app.state, "llm_status", None)
    if cached and cached.get("provider") not in (None, "none"):
        return LLMStatusResponse(**cached)

    try:
        llm = await get_llm_router()
        status = await llm.get_status()
        request.app.state.llm_status = status
        return LLMStatusResponse(**status)
    except Exception:
        return LLMStatusResponse(**_DEFAULT_LLM)


@router.get("/proxy/status")
async def proxy_status() -> dict:
    return await get_pool_stats()
