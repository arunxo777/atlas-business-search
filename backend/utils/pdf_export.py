"""Detailed PDF research report export."""

from __future__ import annotations

import io
import re
from datetime import datetime
from typing import Any

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    HRFlowable,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from models import BusinessRecord, ResearchJob
from utils.data_quality import build_research_report

_PAGE_W, _PAGE_H = A4


def _esc(text: str | None) -> str:
    if not text:
        return ""
    return (
        str(text)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


def _join(items: list[str] | None, sep: str = ", ") -> str:
    if not items:
        return "—"
    cleaned = [i.strip() for i in items if i and str(i).strip()]
    return _esc(sep.join(cleaned)) if cleaned else "—"


def _slug_filename(query: str) -> str:
    slug = re.sub(r"[^\w\s-]", "", query.lower())
    slug = re.sub(r"[\s_-]+", "-", slug).strip("-")[:40]
    return f"atlas-research-{slug or 'report'}.pdf"


def _styles() -> dict[str, ParagraphStyle]:
    base = getSampleStyleSheet()
    return {
        "title": ParagraphStyle(
            "Title",
            parent=base["Heading1"],
            fontSize=20,
            leading=24,
            spaceAfter=6,
            textColor=colors.HexColor("#111827"),
        ),
        "subtitle": ParagraphStyle(
            "Subtitle",
            parent=base["Normal"],
            fontSize=10,
            leading=14,
            textColor=colors.HexColor("#6B7280"),
            spaceAfter=12,
        ),
        "h2": ParagraphStyle(
            "H2",
            parent=base["Heading2"],
            fontSize=13,
            leading=16,
            spaceBefore=14,
            spaceAfter=8,
            textColor=colors.HexColor("#1F2937"),
        ),
        "h3": ParagraphStyle(
            "H3",
            parent=base["Heading3"],
            fontSize=11,
            leading=14,
            spaceBefore=10,
            spaceAfter=4,
            textColor=colors.HexColor("#374151"),
        ),
        "body": ParagraphStyle(
            "Body",
            parent=base["Normal"],
            fontSize=9,
            leading=12,
            textColor=colors.HexColor("#374151"),
        ),
        "label": ParagraphStyle(
            "Label",
            parent=base["Normal"],
            fontSize=8,
            leading=10,
            textColor=colors.HexColor("#6B7280"),
        ),
        "mono": ParagraphStyle(
            "Mono",
            parent=base["Code"],
            fontSize=7,
            leading=9,
            textColor=colors.HexColor("#4B5563"),
            wordWrap="CJK",
        ),
    }


def _summary_table(rows: list[tuple[str, str]]) -> Table:
    data = [[Paragraph(f"<b>{_esc(k)}</b>", _styles()["body"]), Paragraph(_esc(v), _styles()["body"])] for k, v in rows]
    table = Table(data, colWidths=[1.6 * inch, 4.6 * inch])
    table.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("LINEBELOW", (0, 0), (-1, -1), 0.25, colors.HexColor("#E5E7EB")),
            ]
        )
    )
    return table


def _field_block(label: str, value: str, styles: dict[str, ParagraphStyle]) -> list[Any]:
    display = value if value and value.strip() and value.strip() != "—" else "—"
    return [
        Paragraph(f"<b>{_esc(label)}</b>", styles["label"]),
        Paragraph(display, styles["body"]),
        Spacer(1, 4),
    ]


def _sources_block(
    business: BusinessRecord, styles: dict[str, ParagraphStyle]
) -> list[Any]:
    if not business.source_urls:
        return []
    lines: list[Any] = [
        Paragraph("<b>Field sources</b>", styles["h3"]),
    ]
    for field, urls in sorted(business.source_urls.items()):
        url_text = "; ".join(urls[:3])
        if len(urls) > 3:
            url_text += f" (+{len(urls) - 3} more)"
        lines.append(
            Paragraph(
                f"<b>{_esc(field.replace('_', ' ').title())}:</b> {_esc(url_text)}",
                styles["mono"],
            )
        )
    lines.append(Spacer(1, 6))
    return lines


def _business_section(
    rank: int,
    business: BusinessRecord,
    styles: dict[str, ParagraphStyle],
) -> list[Any]:
    story: list[Any] = []
    title = f"#{rank} · {_esc(business.business_name)}"
    story.append(Paragraph(title, styles["h2"]))
    meta = (
        f"Verification: {_esc(business.verification_status.replace('_', ' ').title())} · "
        f"Rank score: {business.rank_score:.1f} · "
        f"Source reliability: {business.source_reliability_score:.2f}"
    )
    story.append(Paragraph(meta, styles["subtitle"]))

    hours = "—"
    if business.working_hours:
        hours = "; ".join(f"{k}: {v}" for k, v in business.working_hours.items())

    social = "—"
    if business.social_profiles:
        social = "; ".join(f"{k}: {v}" for k, v in business.social_profiles.items())

    story.extend(
        _field_block("Address", _esc(business.address or "—"), styles)
    )
    story.extend(_field_block("Phone", _join(business.phone), styles))
    story.extend(_field_block("Email", _join(business.email), styles))
    story.extend(_field_block("Website", _esc(business.website or "—"), styles))
    story.extend(_field_block("Working hours", _esc(hours), styles))

    rating = "—"
    if business.rating is not None:
        rating = f"{business.rating}"
        if business.review_count is not None:
            rating += f" ({business.review_count} reviews)"
    story.extend(_field_block("Rating", _esc(rating), styles))

    story.extend(_field_block("Services", _join(business.services), styles))
    story.extend(_field_block("Specialties", _join(business.specialties), styles))
    story.extend(
        _field_block("License", _esc(business.license_information or "—"), styles)
    )
    story.extend(_field_block("Certifications", _join(business.certifications), styles))
    story.extend(_field_block("Awards", _join(business.awards), styles))
    story.extend(_field_block("Social profiles", _esc(social), styles))

    if business.image_urls:
        story.extend(
            _field_block("Images", _join(business.image_urls[:5]), styles)
        )

    if business.verification_details:
        details = "; ".join(
            f"{k}: {v}" for k, v in business.verification_details.items()
        )
        story.extend(_field_block("Verification notes", _esc(details), styles))

    story.extend(_sources_block(business, styles))

    if business.raw_sources:
        story.append(Paragraph("<b>Raw source URLs</b>", styles["h3"]))
        for url in business.raw_sources[:8]:
            story.append(Paragraph(_esc(url), styles["mono"]))
        if len(business.raw_sources) > 8:
            story.append(
                Paragraph(
                    _esc(f"... and {len(business.raw_sources) - 8} more"),
                    styles["label"],
                )
            )

    story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#E5E7EB")))
    story.append(Spacer(1, 8))
    return story


def export_research_pdf(
    job: ResearchJob,
    businesses: list[BusinessRecord],
    active_sources: list[str] | None = None,
) -> bytes:
    """Build a multi-page PDF with summary + full detail per business."""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=0.75 * inch,
        rightMargin=0.75 * inch,
        topMargin=0.75 * inch,
        bottomMargin=0.75 * inch,
        title=f"Atlas Research — {job.query}",
        author="Atlas Research",
    )

    styles = _styles()
    story: list[Any] = []
    report = build_research_report(job, businesses, active_sources)
    summary = report.get("search_summary", {})
    quality = report.get("data_quality_summary", {})

    generated = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")

    story.append(Paragraph("Atlas Research Report", styles["title"]))
    story.append(
        Paragraph(
            f"Query: <b>{_esc(job.query)}</b><br/>"
            f"Generated: {_esc(generated)} · Job ID: {_esc(job.id[:8])}…",
            styles["subtitle"],
        )
    )
    story.append(Spacer(1, 8))

    story.append(Paragraph("Search summary", styles["h2"]))
    summary_rows = [
        ("Category", str(summary.get("category") or job.category or "—")),
        ("Location", str(summary.get("location") or job.location or "—")),
        ("Businesses found", str(summary.get("businesses_found", job.businesses_found))),
        ("Verified", str(summary.get("businesses_verified", job.businesses_verified))),
        ("Duplicates removed", str(summary.get("duplicates_removed", job.duplicates_removed))),
        ("Sources searched", str(summary.get("sources_searched", job.sources_searched))),
        (
            "Duration",
            f"{summary.get('research_duration_seconds') or job.duration_seconds or '—'}s"
            if (summary.get("research_duration_seconds") or job.duration_seconds)
            else "—",
        ),
        ("LLM provider", str(summary.get("llm_provider") or job.llm_provider or "—")),
    ]
    active = summary.get("active_sources") or active_sources or []
    if active:
        summary_rows.append(("Active sources", ", ".join(active)))
    story.append(_summary_table(summary_rows))
    story.append(Spacer(1, 12))

    if quality:
        story.append(Paragraph("Data quality (% of records)", styles["h2"]))
        q_rows = [
            ("With website", f"{quality.get('records_with_website', 0)}%"),
            ("With phone", f"{quality.get('records_with_phone', 0)}%"),
            ("With email", f"{quality.get('records_with_email', 0)}%"),
            ("With address", f"{quality.get('records_with_address', 0)}%"),
            ("With hours", f"{quality.get('records_with_working_hours', 0)}%"),
            ("With license", f"{quality.get('records_with_license', 0)}%"),
            ("With rating", f"{quality.get('records_with_rating', 0)}%"),
            ("Highly verified", f"{quality.get('records_highly_verified', 0)}%"),
        ]
        story.append(_summary_table(q_rows))

    story.append(PageBreak())
    story.append(Paragraph("Business listings (full detail)", styles["title"]))
    story.append(
        Paragraph(
            f"{len(businesses)} businesses ranked by trust score.",
            styles["subtitle"],
        )
    )
    story.append(Spacer(1, 8))

    if not businesses:
        story.append(Paragraph("No businesses found for this query.", styles["body"]))
    else:
        sorted_biz = sorted(
            businesses,
            key=lambda b: (
                b.rank_position if b.rank_position > 0 else 999999,
                -b.rank_score,
            ),
        )
        if sorted_biz[0].rank_position == 0:
            sorted_biz = sorted(
                businesses,
                key=lambda b: b.rank_score,
                reverse=True,
            )
        for idx, business in enumerate(sorted_biz, start=1):
            story.extend(_business_section(idx, business, styles))
            if idx < len(sorted_biz) and idx % 3 == 0:
                story.append(PageBreak())

    doc.build(story)
    buffer.seek(0)
    return buffer.read()


def pdf_filename_for_query(query: str) -> str:
    return _slug_filename(query)
