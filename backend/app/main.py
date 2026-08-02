"""AI Research OS — FastAPI application entry point."""

import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import chat, experiments, health, knowledge, papers, projects, research, scientist
from app.config import get_settings
from app.database.postgres import init_db
from app.database.redis_client import redis_client

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
settings = get_settings()

INFRA_TIMEOUT_SEC = 3


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting %s...", settings.app_name)
    app.state.postgres_ok = False
    app.state.redis_ok = False

    try:
        await asyncio.wait_for(init_db(), timeout=INFRA_TIMEOUT_SEC)
        app.state.postgres_ok = True
        logger.info("PostgreSQL initialized")
    except Exception as e:
        logger.warning("PostgreSQL init failed (degraded mode): %s", e)

    try:
        await asyncio.wait_for(redis_client.connect(), timeout=INFRA_TIMEOUT_SEC)
        app.state.redis_ok = True
        logger.info("Redis connected")
    except Exception as e:
        logger.warning("Redis unavailable (degraded mode): %s", e)

    yield
    await redis_client.disconnect()
    logger.info("Shutdown complete")


app = FastAPI(
    title=settings.app_name,
    description="AI-driven automated research platform",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_origin_regex=(
        r"http://(localhost|127\.0\.0\.1):\d+"
        if settings.app_env == "development"
        else None
    ),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

API_PREFIX = "/api/v1"
app.include_router(health.router)
app.include_router(chat.router, prefix=API_PREFIX)
app.include_router(research.router, prefix=API_PREFIX)
app.include_router(papers.router, prefix=API_PREFIX)
app.include_router(projects.router, prefix=API_PREFIX)
app.include_router(knowledge.router, prefix=API_PREFIX)
app.include_router(experiments.router, prefix=API_PREFIX)
app.include_router(scientist.router, prefix=API_PREFIX)
