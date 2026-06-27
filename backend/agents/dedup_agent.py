"""Deduplication agent — fuzzy matching + LLM confirmation."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from rapidfuzz import fuzz

from config import Settings, get_settings
from llm.prompts import dedup_prompt
from llm.router import LLMRouter
from models import BusinessRecord, utcnow
from utils.normalizer import (
    extract_city,
    normalize_address,
    normalize_business_name,
    normalize_phone,
)
from utils.source_scorer import score_source_type

logger = logging.getLogger(__name__)

STATUS_RANK = {
    "highly_verified": 4,
    "verified": 3,
    "unverified": 2,
    "conflicted": 1,
}


class DedupAgent:
    def __init__(self, llm: LLMRouter, settings: Settings | None = None) -> None:
        self.llm = llm
        self.settings = settings or get_settings()
        self.llm_semaphore = asyncio.Semaphore(2 if self.settings.fast_mode else 5)

    async def deduplicate(
        self, businesses: list[BusinessRecord]
    ) -> tuple[list[BusinessRecord], int]:
        if not businesses:
            return [], 0

        merged_indices: set[int] = set()
        duplicates_removed = 0
        result: list[BusinessRecord] = []

        phone_map: dict[str, int] = {}
        for idx, biz in enumerate(businesses):
            for phone in biz.phone:
                norm = normalize_phone(phone)
                if norm:
                    if norm in phone_map:
                        primary_idx = phone_map[norm]
                        if primary_idx not in merged_indices and idx not in merged_indices:
                            businesses[primary_idx] = self._merge_records(
                                businesses[primary_idx], biz
                            )
                            merged_indices.add(idx)
                            duplicates_removed += 1
                    else:
                        phone_map[norm] = idx

        candidates: list[tuple[int, int, float]] = []
        active = [i for i in range(len(businesses)) if i not in merged_indices]

        for i in range(len(active)):
            for j in range(i + 1, len(active)):
                idx_a, idx_b = active[i], active[j]
                if idx_a in merged_indices or idx_b in merged_indices:
                    continue

                biz_a, biz_b = businesses[idx_a], businesses[idx_b]
                name_a = normalize_business_name(biz_a.business_name)
                name_b = normalize_business_name(biz_b.business_name)
                ratio = fuzz.token_sort_ratio(name_a, name_b)

                city_a = extract_city(biz_a.address)
                city_b = extract_city(biz_b.address)
                same_city = not city_a or not city_b or city_a == city_b

                if ratio >= 90 and same_city:
                    businesses[idx_a] = self._merge_records(biz_a, biz_b)
                    merged_indices.add(idx_b)
                    duplicates_removed += 1
                elif 70 <= ratio < 90 and same_city:
                    candidates.append((idx_a, idx_b, ratio))

        candidates.sort(key=lambda x: x[2], reverse=True)
        candidates = candidates[: self.settings.max_llm_dedup_pairs]

        llm_merged = await self._llm_confirm_candidates(businesses, candidates)
        for idx_b in llm_merged:
            merged_indices.add(idx_b)
            duplicates_removed += 1

        for idx, biz in enumerate(businesses):
            if idx not in merged_indices:
                result.append(biz)

        return result, duplicates_removed

    async def _llm_confirm_candidates(
        self,
        businesses: list[BusinessRecord],
        candidates: list[tuple[int, int, float]],
    ) -> set[int]:
        merged: set[int] = set()

        async def _check_pair(idx_a: int, idx_b: int) -> tuple[int, int, bool]:
            biz_a = businesses[idx_a]
            biz_b = businesses[idx_b]
            async with self.llm_semaphore:
                try:
                    messages = dedup_prompt(
                        biz_a.model_dump(),
                        biz_b.model_dump(),
                    )
                    result = await self.llm.complete_json(messages)
                    if (
                        isinstance(result, dict)
                        and result.get("is_same")
                        and float(result.get("confidence", 0)) > 0.8
                    ):
                        return idx_a, idx_b, True
                except Exception as exc:
                    logger.warning("LLM dedup failed: %s", exc)
            return idx_a, idx_b, False

        tasks = [_check_pair(a, b) for a, b, _ in candidates]
        results = await asyncio.gather(*tasks)

        for idx_a, idx_b, is_same in results:
            if is_same and idx_b not in merged:
                businesses[idx_a] = self._merge_records(
                    businesses[idx_a], businesses[idx_b]
                )
                merged.add(idx_b)

        return merged

    def _merge_records(
        self, primary: BusinessRecord, secondary: BusinessRecord
    ) -> BusinessRecord:
        if secondary.non_null_field_count() > primary.non_null_field_count():
            primary, secondary = secondary, primary

        for phone in secondary.phone:
            if phone not in primary.phone:
                primary.phone.append(phone)
                for url in secondary.source_urls.get("phone", []):
                    primary.source_urls.setdefault("phone", []).append(url)

        for email in secondary.email:
            if email not in primary.email:
                primary.email.append(email)
                for url in secondary.source_urls.get("email", []):
                    primary.source_urls.setdefault("email", []).append(url)

        for field in ("address", "website", "working_hours", "license_information"):
            primary_val = getattr(primary, field)
            secondary_val = getattr(secondary, field)
            if not primary_val and secondary_val:
                setattr(primary, field, secondary_val)
                for url in secondary.source_urls.get(field, []):
                    primary.source_urls.setdefault(field, []).append(url)
            elif primary_val and secondary_val and primary_val != secondary_val:
                primary_score = primary.source_reliability_score
                secondary_score = secondary.source_reliability_score
                if secondary_score > primary_score:
                    setattr(primary, field, secondary_val)

        for field in ("services", "specialties", "certifications", "awards", "image_urls", "raw_sources"):
            primary_list = getattr(primary, field)
            for item in getattr(secondary, field):
                if item not in primary_list:
                    primary_list.append(item)

        for key, urls in secondary.source_urls.items():
            for url in urls:
                if url not in primary.source_urls.get(key, []):
                    primary.source_urls.setdefault(key, []).append(url)

        for platform, url in secondary.social_profiles.items():
            if platform not in primary.social_profiles:
                primary.social_profiles[platform] = url

        if secondary.rating is not None and (
            primary.rating is None or secondary.source_reliability_score > primary.source_reliability_score
        ):
            primary.rating = secondary.rating
            primary.review_count = secondary.review_count

        primary.source_reliability_score = max(
            primary.source_reliability_score,
            secondary.source_reliability_score,
        )
        primary.last_updated = utcnow()
        return primary
