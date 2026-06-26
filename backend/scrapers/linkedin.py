"""LinkedIn company public page scraper."""

from __future__ import annotations

import logging

from llm.router import LLMRouter
from models import BusinessRecord
from scrapers.generic import GenericScraper

logger = logging.getLogger(__name__)


class LinkedInScraper:
    def __init__(self, llm: LLMRouter, job_id: str) -> None:
        self.llm = llm
        self.job_id = job_id
        self.generic = GenericScraper(llm, job_id)

    async def scrape_url(self, url: str) -> list[BusinessRecord]:
        if "linkedin.com" not in url:
            return []
        records = await self.generic.scrape_url(url, "linkedin")
        for record in records:
            if "linkedin" not in record.social_profiles:
                record.social_profiles["linkedin"] = url
        return records
