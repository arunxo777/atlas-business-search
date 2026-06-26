"""Verification agent — cross-source field verification and conflict detection."""

from __future__ import annotations

import logging
from typing import Any

from llm.prompts import verify_prompt
from llm.router import LLMRouter
from models import BusinessRecord, VerificationStatus, utcnow
from utils.source_scorer import weighted_average

logger = logging.getLogger(__name__)

FIELD_STATUS_RANK = {
    "highly_verified": 4,
    "verified": 3,
    "unverified": 2,
    "conflicted": 1,
}

VERIFY_FIELDS = ["phone", "email", "address", "working_hours", "license_information"]


class VerificationAgent:
    def __init__(self, llm: LLMRouter) -> None:
        self.llm = llm

    async def verify(self, businesses: list[BusinessRecord]) -> list[BusinessRecord]:
        verified: list[BusinessRecord] = []
        for business in businesses:
            try:
                verified.append(await self._verify_one(business))
            except Exception as exc:
                logger.error("Verification failed for %s: %s", business.business_name, exc)
                verified.append(business)
        return verified

    async def _verify_one(self, business: BusinessRecord) -> BusinessRecord:
        field_statuses: list[VerificationStatus] = []
        all_scores: list[tuple[float, float]] = []

        for field in VERIFY_FIELDS:
            status, detail, scores = await self._verify_field(business, field)
            business.verification_details[field] = detail
            field_statuses.append(status)
            all_scores.extend(scores)

        business.verification_status = self._overall_status(field_statuses)
        business.source_reliability_score = weighted_average(all_scores) if all_scores else business.source_reliability_score
        business.last_updated = utcnow()
        return business

    async def _verify_field(
        self, business: BusinessRecord, field: str
    ) -> tuple[VerificationStatus, dict[str, Any], list[tuple[float, float]]]:
        value = getattr(business, field)
        source_urls = business.source_urls.get(field, business.raw_sources)

        if not value:
            return "unverified", {"sources": [], "conflicts": []}, []

        if isinstance(value, list):
            values_with_sources = [
                {"value": v, "source_url": url, "score": business.source_reliability_score}
                for v in value
                for url in (source_urls or business.raw_sources[:1])
            ]
        else:
            values_with_sources = [
                {
                    "value": value,
                    "source_url": url,
                    "score": business.source_reliability_score,
                }
                for url in (source_urls or business.raw_sources[:1])
            ]

        unique_values = {str(v["value"]) for v in values_with_sources}
        scores = [(v["score"], 1.0) for v in values_with_sources]

        source_count = len(source_urls) if source_urls else len(business.raw_sources)
        reliability = business.source_reliability_score

        if len(values_with_sources) <= 1 or len(unique_values) <= 1:
            if source_count >= 3:
                status: VerificationStatus = "highly_verified"
            elif source_count >= 2 or reliability >= 0.85:
                status = "verified"
            elif source_count >= 1 and reliability >= 0.75:
                status = "verified"
            else:
                status = "unverified"
            return status, {"sources": values_with_sources, "conflicts": []}, scores

        try:
            messages = verify_prompt(field, values_with_sources)
            result = await self.llm.complete_json(messages)
            if isinstance(result, dict):
                conflicts = result.get("conflicts", [])
                if conflicts:
                    return (
                        "conflicted",
                        {
                            "sources": values_with_sources,
                            "conflicts": conflicts,
                            "verified_value": result.get("verified_value"),
                            "confidence": result.get("confidence"),
                        },
                        scores,
                    )
        except Exception as exc:
            logger.warning("LLM verify failed for field %s: %s", field, exc)

        return (
            "conflicted",
            {"sources": values_with_sources, "conflicts": list(unique_values)},
            scores,
        )

    @staticmethod
    def _overall_status(statuses: list[VerificationStatus]) -> VerificationStatus:
        if not statuses:
            return "unverified"
        if "conflicted" in statuses:
            return "conflicted"
        if sum(1 for s in statuses if s == "highly_verified") >= 2:
            return "highly_verified"
        verified_or_better = sum(
            1 for s in statuses if s in ("highly_verified", "verified")
        )
        if verified_or_better >= 2:
            return "verified"
        if any(s == "highly_verified" for s in statuses):
            return "highly_verified"
        if any(s == "verified" for s in statuses):
            return "verified"
        return "unverified"
