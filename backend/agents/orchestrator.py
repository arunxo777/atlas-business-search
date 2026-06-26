"""Main research orchestrator — coordinates the full agent pipeline."""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Callable, Awaitable

from agents.dedup_agent import DedupAgent
from agents.enrichment_agent import EnrichmentAgent
from agents.scraper_agent import ScraperAgent
from agents.search_agent import SearchAgent
from agents.verification_agent import VerificationAgent
from config import Settings, get_settings
from database import Database
from llm.prompts import parse_query_prompt
from llm.router import LLMRouter, get_llm_router
from models import BusinessRecord, ResearchJob, ResearchRequest, SSEEvent, utcnow
from utils.data_quality import build_research_report
from utils.field_validator import validate_business_record
from utils.ranking import rank_businesses
from utils.source_recommendations import attach_recommendations

logger = logging.getLogger(__name__)

EventCallback = Callable[[SSEEvent], Awaitable[None]]


class ResearchOrchestrator:
    PHASE_PROGRESS = {
        "queued": 0,
        "searching": 10,
        "scraping": 30,
        "enriching": 60,
        "deduplicating": 75,
        "verifying": 85,
        "complete": 100,
    }

    def __init__(
        self,
        db: Database,
        settings: Settings | None = None,
    ) -> None:
        self.db = db
        self.settings = settings or get_settings()
        self.llm: LLMRouter | None = None

    async def _emit(
        self,
        event_queue: asyncio.Queue[SSEEvent | None],
        event: str,
        data: dict,
    ) -> None:
        await event_queue.put(SSEEvent(event=event, data=data))

    async def run(
        self,
        job_id: str,
        request: ResearchRequest,
        event_queue: asyncio.Queue[SSEEvent | None],
    ) -> None:
        start_time = time.perf_counter()
        businesses: list[BusinessRecord] = []

        try:
            force_provider = request.llm_provider if request.llm_provider != "auto" else None
            self.llm = await get_llm_router(force_provider=force_provider)

            provider_name = (
                self.llm.active_provider.get("name", "auto")
                if self.llm.active_provider
                else "auto"
            )
            await self.db.update_job(
                job_id,
                llm_provider=provider_name,
                status="searching",
                progress_pct=self.PHASE_PROGRESS["searching"],
            )
            await self._emit(
                event_queue,
                "progress",
                {
                    "phase": "searching",
                    "progress_pct": self.PHASE_PROGRESS["searching"],
                    "message": "Parsing query and searching sources...",
                },
            )

            category, location = await self._parse_query(request.query)
            await self.db.update_job(job_id, category=category, location=location)

            search_agent = SearchAgent(self.settings)
            search_results = await search_agent.find_urls(category, location)

            bootstrap_businesses = await search_agent.fetch_bootstrap_businesses(
                category, location, job_id
            )
            for record in bootstrap_businesses:
                record.job_id = job_id
                record = validate_business_record(record)
                if not record.business_name:
                    continue
                businesses.append(record)
                await self.db.update_job(job_id, businesses_found=len(businesses))
                await self._emit(
                    event_queue, "business", record.model_dump(mode="json")
                )
            if bootstrap_businesses:
                sources = []
                if self.settings.use_serpapi and self.settings.serpapi_key:
                    sources.append("SerpAPI")
                if self.settings.use_firecrawl and self.settings.firecrawl_api_key:
                    sources.append("Firecrawl")
                if self.settings.use_omkar_google_scraper:
                    sources.append("Google Scraper")
                sources.append("YP/Yelp/Maps/Bing")
                source_label = " + ".join(sources)
                await self._emit(
                    event_queue,
                    "progress",
                    {
                        "phase": "searching",
                        "progress_pct": self.PHASE_PROGRESS["searching"] + 5,
                        "message": f"{source_label}: found {len(bootstrap_businesses)} local businesses",
                    },
                )

            sources_count = len(search_results)

            await self.db.update_job(
                job_id,
                sources_searched=sources_count,
                status="scraping",
                progress_pct=self.PHASE_PROGRESS["scraping"],
            )
            await self._emit(
                event_queue,
                "progress",
                {
                    "phase": "scraping",
                    "progress_pct": self.PHASE_PROGRESS["scraping"],
                    "message": f"Found {sources_count} sources. Scraping...",
                    "sources_found": sources_count,
                },
            )

            scraper_agent = ScraperAgent(self.llm, job_id, self.settings)

            async def on_business_found(record: BusinessRecord) -> None:
                record.job_id = job_id
                businesses.append(record)
                await self.db.update_job(
                    job_id, businesses_found=len(businesses)
                )
                await self._emit(
                    event_queue,
                    "business",
                    record.model_dump(mode="json"),
                )

            scraped = await scraper_agent.scrape_all(
                search_results,
                category,
                location,
                on_business_found=on_business_found,
                max_results=min(request.max_results, self.settings.max_businesses_per_query),
            )

            if not businesses:
                businesses = scraped
                for record in businesses:
                    record.job_id = job_id

            await self.db.update_job(
                job_id,
                status="enriching",
                progress_pct=self.PHASE_PROGRESS["enriching"],
                businesses_found=len(businesses),
            )
            await self._emit(
                event_queue,
                "progress",
                {
                    "phase": "enriching",
                    "progress_pct": self.PHASE_PROGRESS["enriching"],
                    "message": f"Enriching {len(businesses)} businesses...",
                },
            )

            enrichment_agent = EnrichmentAgent(
                self.llm, job_id, search_agent, self.settings
            )
            businesses = await enrichment_agent.enrich(businesses, location)

            await self.db.update_job(
                job_id,
                status="deduplicating",
                progress_pct=self.PHASE_PROGRESS["deduplicating"],
            )
            await self._emit(
                event_queue,
                "progress",
                {
                    "phase": "deduplicating",
                    "progress_pct": self.PHASE_PROGRESS["deduplicating"],
                    "message": "Deduplicating results...",
                },
            )

            dedup_agent = DedupAgent(self.llm)
            businesses, dupes_removed = await dedup_agent.deduplicate(businesses)

            await self.db.update_job(
                job_id,
                duplicates_removed=dupes_removed,
                businesses_found=len(businesses),
                status="deduplicating",
                progress_pct=self.PHASE_PROGRESS["deduplicating"],
            )
            await self._emit(
                event_queue,
                "progress",
                {
                    "phase": "deduplicating",
                    "progress_pct": self.PHASE_PROGRESS["deduplicating"],
                    "message": f"Removed {dupes_removed} duplicates",
                    "removed": dupes_removed,
                },
            )

            await self.db.update_job(
                job_id,
                progress_pct=self.PHASE_PROGRESS["deduplicating"] + 5,
            )
            await self._emit(
                event_queue,
                "progress",
                {
                    "phase": "verifying",
                    "progress_pct": self.PHASE_PROGRESS.get("verifying", 85),
                    "message": "Verifying business data...",
                },
            )

            verification_agent = VerificationAgent(self.llm)
            businesses = await verification_agent.verify(businesses)

            businesses = [
                validate_business_record(b) for b in businesses if b.business_name
            ]
            businesses = attach_recommendations(businesses)
            businesses = rank_businesses(businesses)

            verified_count = sum(
                1
                for b in businesses
                if b.verification_status in ("verified", "highly_verified")
            )

            for business in businesses:
                business.job_id = job_id
                await self.db.upsert_business(business)

            duration = time.perf_counter() - start_time
            warning = None
            if not businesses:
                warning = (
                    "No businesses found. Common causes: search rate limits, "
                    "blocked sites, or Ollama out of memory. Try a smaller model "
                    "(e.g. gemma2:2b) or ensure Ollama is running."
                )

            await self.db.update_job(
                job_id,
                status="complete",
                progress_pct=100,
                businesses_found=len(businesses),
                businesses_verified=verified_count,
                duplicates_removed=dupes_removed,
                duration_seconds=duration,
                completed_at=utcnow(),
                error=warning,
            )

            job = await self.db.get_job(job_id)
            active_sources = self._active_source_labels()
            report = (
                build_research_report(job, businesses, active_sources)
                if job
                else {}
            )
            summary_payload = job.model_dump(mode="json") if job else {}
            summary_payload["research_report"] = report
            await self._emit(
                event_queue,
                "summary",
                summary_payload,
            )
            if warning:
                await self._emit(event_queue, "progress", {
                    "phase": "complete",
                    "progress_pct": 100,
                    "message": warning,
                })

        except Exception as exc:
            logger.exception("Research job %s failed", job_id)
            duration = time.perf_counter() - start_time
            await self.db.update_job(
                job_id,
                status="failed",
                error=str(exc),
                duration_seconds=duration,
                completed_at=utcnow(),
            )
            await self._emit(
                event_queue,
                "error",
                {"message": str(exc)},
            )
        finally:
            await event_queue.put(None)

    async def _parse_query(self, query: str) -> tuple[str, str]:
        if not self.llm:
            self.llm = await get_llm_router()

        try:
            messages = parse_query_prompt(query)
            result = await self.llm.complete_json(messages)
            if isinstance(result, dict):
                category = result.get("category", query)
                location = result.get("location", "")
                return str(category), str(location)
        except Exception as exc:
            logger.warning("LLM query parse failed, using heuristic: %s", exc)

        parts = query.lower().split(" in ")
        if len(parts) >= 2:
            return parts[0].strip().title(), parts[-1].strip().title()
        return query.strip(), ""

    def _active_source_labels(self) -> list[str]:
        labels = ["DuckDuckGo", "Bing", "YP/Yelp/Maps"]
        if self.settings.use_serpapi and self.settings.serpapi_key:
            labels.append("SerpAPI")
        if self.settings.use_firecrawl and self.settings.firecrawl_api_key:
            labels.append("Firecrawl")
        if self.settings.use_omkar_google_scraper:
            labels.append("Google Scraper")
        labels.append("Playwright/crawl4ai")
        if self.settings.use_proxy_pool:
            labels.append("Proxy Pool")
        return labels
