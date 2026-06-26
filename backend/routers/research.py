"""Research job endpoints with SSE streaming."""

from __future__ import annotations

import asyncio
import json
import logging
from typing import AsyncGenerator

from fastapi import APIRouter, HTTPException, Request
from sse_starlette.sse import EventSourceResponse

from agents.orchestrator import ResearchOrchestrator
from database import get_database
from models import ResearchJob, ResearchRequest, ResearchResponse, SSEEvent

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/research", tags=["research"])

_job_queues: dict[str, asyncio.Queue[SSEEvent | None]] = {}
_running_tasks: dict[str, asyncio.Task] = {}


def _get_or_create_queue(job_id: str) -> asyncio.Queue[SSEEvent | None]:
    if job_id not in _job_queues:
        _job_queues[job_id] = asyncio.Queue()
    return _job_queues[job_id]


@router.post("", response_model=ResearchResponse)
async def start_research(request: ResearchRequest) -> ResearchResponse:
    db = await get_database()

    cached_job_id = await db.check_cache(request.query)
    if cached_job_id:
        return ResearchResponse(
            job_id=cached_job_id,
            status="complete",
            cached=True,
        )

    job = ResearchJob(
        query=request.query,
        llm_provider=request.llm_provider or "auto",
    )
    await db.create_job(job)

    event_queue = _get_or_create_queue(job.id)
    orchestrator = ResearchOrchestrator(db)

    task = asyncio.create_task(
        orchestrator.run(job.id, request, event_queue)
    )
    _running_tasks[job.id] = task

    def _cleanup(t: asyncio.Task) -> None:
        _running_tasks.pop(job.id, None)

    task.add_done_callback(_cleanup)

    return ResearchResponse(job_id=job.id, status="queued")


@router.get("/{job_id}", response_model=ResearchJob)
async def get_research_job(job_id: str) -> ResearchJob:
    db = await get_database()
    job = await db.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@router.get("/{job_id}/stream")
async def stream_research(job_id: str, request: Request) -> EventSourceResponse:
    db = await get_database()
    job = await db.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    event_queue = _get_or_create_queue(job_id)

    async def event_generator() -> AsyncGenerator[dict, None]:
        if job.status == "complete":
            businesses, _ = await db.get_businesses_by_job(job_id)
            yield {
                "event": "progress",
                "data": json.dumps({
                    "phase": "complete",
                    "progress_pct": 100,
                    "message": "Job already complete (cached)",
                }),
            }
            for biz in businesses:
                yield {
                    "event": "business",
                    "data": json.dumps(biz.model_dump(mode="json"), default=str),
                }
            yield {
                "event": "summary",
                "data": json.dumps(job.model_dump(mode="json"), default=str),
            }
            return

        while True:
            if await request.is_disconnected():
                break
            try:
                event = await asyncio.wait_for(event_queue.get(), timeout=30.0)
            except asyncio.TimeoutError:
                yield {"event": "ping", "data": "{}"}
                continue

            if event is None:
                final_job = await db.get_job(job_id)
                if final_job and final_job.status == "complete":
                    yield {
                        "event": "summary",
                        "data": json.dumps(
                            final_job.model_dump(mode="json"), default=str
                        ),
                    }
                break

            yield {
                "event": event.event,
                "data": json.dumps(event.data, default=str),
            }

        _job_queues.pop(job_id, None)

    return EventSourceResponse(event_generator())
