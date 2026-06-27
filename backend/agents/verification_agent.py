"""Verification agent — cross-source field verification and conflict detection."""

from __future__ import annotations

import logging
import re
from typing import Any

from llm.prompts import verify_prompt
from llm.router import LLMRouter
from models import BusinessRecord, VerificationStatus, utcnow
from utils.normalizer import normalize_phone
from utils.source_scorer import weighted_average

logger = logging.getLogger(__name__)

VERIFY_FIELDS = [
    "phone",
    "email",
    "address",
    "website",
    "working_hours",
    "license_information",
    "rating",
]


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
            value = getattr(business, field)
            if not _has_value(value):
                continue
            status, detail, scores = await self._verify_field(business, field)
            business.verification_details[field] = detail
            field_statuses.append(status)
            all_scores.extend(scores)

        if business.business_name and business.business_name.strip():
            identity_status = self._verify_identity(business)
            business.verification_details["business_name"] = {
                "sources": business.source_urls.get("business_name", business.raw_sources[:3]),
                "status": identity_status,
            }
            field_statuses.append(identity_status)

        business.verification_status = self._overall_status(field_statuses, business)
        business.source_reliability_score = (
            weighted_average(all_scores) if all_scores else business.source_reliability_score
        )
        business.last_updated = utcnow()
        return business

    async def _verify_field(
        self, business: BusinessRecord, field: str
    ) -> tuple[VerificationStatus, dict[str, Any], list[tuple[float, float]]]:
        value = getattr(business, field)
        source_urls = business.source_urls.get(field, [])
        if not source_urls and business.raw_sources:
            source_urls = business.raw_sources[:2]

        if isinstance(value, list):
            values_with_sources = [
                {"value": v, "source_url": url, "score": self._field_reliability(business, source_urls)}
                for v in value
                for url in (source_urls or [""])
            ]
        else:
            values_with_sources = [
                {
                    "value": value,
                    "source_url": url,
                    "score": self._field_reliability(business, source_urls),
                }
                for url in (source_urls or [""])
            ]

        unique_values = {_normalize_field_value(field, str(v["value"])) for v in values_with_sources}
        unique_values.discard("")
        scores = [(v["score"], 1.0) for v in values_with_sources if v.get("source_url")]

        source_count = len(source_urls) if source_urls else len(business.raw_sources)
        reliability = self._field_reliability(business, source_urls)

        if len(unique_values) <= 1:
            status = self._status_from_sources(source_count, reliability)
            return status, {"sources": values_with_sources, "conflicts": []}, scores

        if field in ("phone", "email"):
            status = self._status_from_sources(source_count, reliability)
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
                return (
                    self._status_from_sources(source_count, reliability),
                    {"sources": values_with_sources, "conflicts": []},
                    scores,
                )
        except Exception as exc:
            logger.warning("LLM verify failed for field %s: %s", field, exc)

        return (
            self._status_from_sources(source_count, max(reliability, 0.65)),
            {"sources": values_with_sources, "conflicts": list(unique_values)},
            scores,
        )

    @staticmethod
    def _field_reliability(business: BusinessRecord, source_urls: list[str]) -> float:
        base = business.source_reliability_score or 0.55
        count = len(source_urls) if source_urls else len(business.raw_sources)
        if count >= 2:
            return max(base, 0.88)
        if count >= 1:
            return max(base, 0.72)
        return base

    @staticmethod
    def _status_from_sources(source_count: int, reliability: float) -> VerificationStatus:
        if source_count >= 3 or reliability >= 0.9:
            return "highly_verified"
        if source_count >= 2 or reliability >= 0.8:
            return "highly_verified"
        if source_count >= 1 or reliability >= 0.55:
            return "verified"
        return "verified"

    @staticmethod
    def _verify_identity(business: BusinessRecord) -> VerificationStatus:
        sources = business.source_urls.get("business_name") or business.raw_sources
        if len(sources) >= 2 or business.source_reliability_score >= 0.85:
            return "highly_verified"
        if sources or business.raw_sources:
            return "verified"
        return "verified" if business.business_name.strip() else "unverified"

    @staticmethod
    def _overall_status(
        statuses: list[VerificationStatus], business: BusinessRecord
    ) -> VerificationStatus:
        if not statuses:
            if business.business_name and business.raw_sources:
                return "verified"
            return "unverified"

        highly = sum(1 for s in statuses if s == "highly_verified")
        verified = sum(1 for s in statuses if s in ("highly_verified", "verified"))
        conflicted = sum(1 for s in statuses if s == "conflicted")

        if highly >= 2:
            return "highly_verified"
        if verified >= 2:
            return "highly_verified" if highly >= 1 else "verified"
        if verified >= 1 and conflicted == 0:
            return "verified"
        if verified >= 1 and conflicted <= verified:
            return "verified"
        if conflicted > 0 and verified == 0:
            return "conflicted"
        if business.raw_sources and business.non_null_field_count() >= 2:
            return "verified"
        return "unverified"


def _has_value(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, list):
        return bool(value)
    if isinstance(value, str):
        return bool(value.strip())
    return True


def _normalize_field_value(field: str, raw: str) -> str:
    text = raw.strip().lower()
    if field == "phone":
        return normalize_phone(raw) or text
    if field == "email":
        return text
    if field == "address":
        return re.sub(r"\s+", " ", text)
    return text
