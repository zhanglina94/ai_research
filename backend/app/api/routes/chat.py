"""Chat API — research assistant conversation."""

import asyncio
import logging
import uuid

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas import ChatRequest, ChatResponse
from app.database.postgres import Conversation, get_db
from app.database.redis_client import get_redis
from app.workflows.research_graph import run_research_chat

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/chat", tags=["chat"])

PERSIST_TIMEOUT_SEC = 3


@router.post("", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    http_request: Request,
    db: AsyncSession = Depends(get_db),
) -> ChatResponse:
    session_id = request.session_id or str(uuid.uuid4())
    redis_ok = getattr(http_request.app.state, "redis_ok", False)
    postgres_ok = getattr(http_request.app.state, "postgres_ok", False)

    history: list[dict] = []
    if redis_ok:
        try:
            redis = await get_redis()
            cached = await redis.get(f"chat:{session_id}")
            if isinstance(cached, list):
                history = cached
        except Exception as e:
            logger.warning("Redis read failed: %s", e)

    history.append({"role": "user", "content": request.message})

    result = await run_research_chat(request.message, history, request.project_id)

    history.append({"role": "assistant", "content": result["reply"]})

    if redis_ok:
        try:
            redis = await get_redis()
            await redis.set(f"chat:{session_id}", history, ttl=7200)
        except Exception as e:
            logger.warning("Redis write failed: %s", e)

    if postgres_ok:
        try:
            db.add(
                Conversation(
                    project_id=request.project_id,
                    role="user",
                    content=request.message,
                )
            )
            db.add(
                Conversation(
                    project_id=request.project_id,
                    role="assistant",
                    content=result["reply"],
                    metadata_=result.get("metadata"),
                )
            )
            await asyncio.wait_for(db.commit(), timeout=PERSIST_TIMEOUT_SEC)
        except Exception as e:
            logger.warning("Failed to persist conversation to PostgreSQL: %s", e)
            try:
                await db.rollback()
            except Exception:
                pass

    return ChatResponse(
        reply=result["reply"],
        session_id=session_id,
        agent=result.get("agent"),
        metadata=result.get("metadata"),
    )
