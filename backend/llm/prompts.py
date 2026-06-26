"""LLM prompt templates for extraction, deduplication, and verification."""

from __future__ import annotations

import json
from typing import Any


BUSINESS_SCHEMA = {
    "business_name": "string (required)",
    "address": "string or null",
    "phone": ["list of phone strings"],
    "email": ["list of email strings"],
    "website": "string or null",
    "working_hours": {"Monday": "9am-5pm", "...": "..."},
    "rating": "float or null",
    "review_count": "int or null",
    "services": ["list of strings"],
    "specialties": ["list of strings"],
    "license_information": "string or null",
    "certifications": ["list of strings"],
    "awards": ["list of strings"],
    "social_profiles": {"facebook": "url", "linkedin": "url"},
    "image_urls": ["list of image URLs"],
}


def extract_business_prompt(html_text: str, query: str) -> list[dict[str, str]]:
    schema_str = json.dumps(BUSINESS_SCHEMA, indent=2)
    truncated = html_text[:20000] if len(html_text) > 20000 else html_text
    return [
        {
            "role": "system",
            "content": (
                "You are a business data extraction expert. Extract ALL businesses "
                "from the provided web page content. Return ONLY valid JSON array. "
                "Never invent data — only extract what is explicitly present in the text. "
                "Use null for missing fields. Use empty arrays for missing lists."
            ),
        },
        {
            "role": "user",
            "content": (
                f"Search query context: {query}\n\n"
                f"Expected output: JSON array of business objects matching this schema:\n"
                f"{schema_str}\n\n"
                f"Web page content:\n{truncated}\n\n"
                "Return ONLY the JSON array, no markdown fences or explanation."
            ),
        },
    ]


def parse_query_prompt(query: str) -> list[dict[str, str]]:
    return [
        {
            "role": "system",
            "content": (
                "You parse business search queries into category and location. "
                "Return ONLY valid JSON."
            ),
        },
        {
            "role": "user",
            "content": (
                f'Parse this search query: "{query}"\n\n'
                'Return JSON: {"category": "business type", "location": "city/region"}\n'
                "Example: 'Cardiologists in Birmingham' -> "
                '{"category": "Cardiologists", "location": "Birmingham"}'
            ),
        },
    ]


def dedup_prompt(business_a: dict[str, Any], business_b: dict[str, Any]) -> list[dict[str, str]]:
    return [
        {
            "role": "system",
            "content": "You are a business deduplication expert.",
        },
        {
            "role": "user",
            "content": (
                "Are these the same business? Consider name similarity, address proximity, "
                "phone overlap.\n\n"
                f"Business A: {json.dumps(business_a, default=str)}\n"
                f"Business B: {json.dumps(business_b, default=str)}\n\n"
                'Return JSON: {"is_same": bool, "confidence": float, "reason": "string"}'
            ),
        },
    ]


def verify_prompt(field: str, values: list[dict[str, Any]]) -> list[dict[str, str]]:
    return [
        {
            "role": "system",
            "content": "You are a data verification expert.",
        },
        {
            "role": "user",
            "content": (
                f"For field '{field}', these values were found from different sources: "
                f"{json.dumps(values, default=str)}\n\n"
                "Identify the most reliable value and flag any conflicts.\n"
                'Return JSON: {"verified_value": any, "confidence": float, '
                '"conflicts": [], "source_scores": {}}'
            ),
        },
    ]
