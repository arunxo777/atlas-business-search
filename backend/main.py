"""FastAPI application entrypoint for the Business Research Agent."""

from __future__ import annotations

import asyncio
import logging
import sys
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Proactor supports subprocess on Windows (required by Playwright).
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

from config import get_settings
from database import get_database
from llm.router import get_llm_router
from routers.health import router as health_router
from routers.research import router as research_router
from routers.results import router as results_router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    logger.info("Starting Business Research Agent...")
    db = await get_database()
    logger.info("Database ready: %s", settings.sqlite_path)
    try:
        llm = await get_llm_router()
        status = await llm.get_status()
        app.state.llm_status = status
        logger.info("LLM ready: %s (%s)", status["provider"], status["model"])
    except RuntimeError as exc:
        app.state.llm_status = {
            "provider": "none",
            "model": "none",
            "latency_ms": None,
            "available_providers": [],
        }
        logger.warning("LLM not available at startup: %s", exc)

    from utils.proxy_pool import get_pool_stats

    proxy_info = await get_pool_stats()
    app.state.proxy_status = proxy_info
    if proxy_info.get("healthy"):
        logger.info("Proxy pool ready: %s", settings.proxy_pool_http)
    elif settings.use_proxy_pool:
        logger.warning(
            "Proxy pool enabled but not reachable at %s — start proxy-in-a-box or set USE_PROXY_POOL=false",
            settings.proxy_pool_api,
        )
    yield
    await db.close()
    logger.info("Shutdown complete")


app = FastAPI(
    title="AI Business Research Agent",
    description="Production-grade business research with multi-source scraping and LLM extraction",
    version="1.0.0",
    lifespan=lifespan,
)

settings = get_settings()
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router, prefix="/api")
app.include_router(research_router, prefix="/api")
app.include_router(results_router, prefix="/api")
