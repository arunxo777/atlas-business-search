"""Results and export endpoints."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import Response

from database import get_database
from models import PaginatedResults, ResearchReport
from utils.data_quality import build_research_report
from utils.export import export_businesses

router = APIRouter(prefix="/results", tags=["results"])


@router.get("/{job_id}", response_model=PaginatedResults)
async def get_results(
    job_id: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=500),
    search: str | None = None,
    sort_by: str = "rank_score",
    sort_order: str = "desc",
    verification_status: str | None = None,
) -> PaginatedResults:
    db = await get_database()
    job = await db.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    items, total = await db.get_businesses_by_job(
        job_id,
        page=page,
        page_size=page_size,
        search=search,
        sort_by=sort_by,
        sort_order=sort_order,
        verification_status=verification_status,
    )
    total_pages = max(1, (total + page_size - 1) // page_size)

    return PaginatedResults(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.get("/{job_id}/report", response_model=ResearchReport)
async def get_research_report(job_id: str) -> ResearchReport:
    db = await get_database()
    job = await db.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    businesses, _ = await db.get_businesses_by_job(
        job_id, page=1, page_size=10000, sort_by="rank_score", sort_order="desc"
    )
    report = build_research_report(job, businesses)
    return ResearchReport(**report)


@router.get("/{job_id}/export")
async def export_results(
    job_id: str,
    format: str = Query("json", pattern="^(json|csv|xlsx)$"),
) -> Response:
    db = await get_database()
    job = await db.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    businesses, _ = await db.get_businesses_by_job(job_id, page=1, page_size=10000)
    content, media_type, filename = export_businesses(businesses, format)  # type: ignore[arg-type]

    return Response(
        content=content,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
