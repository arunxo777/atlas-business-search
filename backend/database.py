"""SQLite database layer with aiosqlite — schema, CRUD, and caching."""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timedelta, timezone
from typing import Any

import aiosqlite

from config import Settings, get_settings
from models import BusinessRecord, ResearchJob, utcnow

logger = logging.getLogger(__name__)

SCHEMA = """
CREATE TABLE IF NOT EXISTS research_jobs (
    id TEXT PRIMARY KEY,
    query TEXT NOT NULL,
    category TEXT DEFAULT '',
    location TEXT DEFAULT '',
    status TEXT NOT NULL DEFAULT 'queued',
    progress_pct REAL DEFAULT 0.0,
    businesses_found INTEGER DEFAULT 0,
    businesses_verified INTEGER DEFAULT 0,
    duplicates_removed INTEGER DEFAULT 0,
    sources_searched INTEGER DEFAULT 0,
    duration_seconds REAL,
    llm_provider TEXT DEFAULT 'auto',
    created_at TEXT NOT NULL,
    completed_at TEXT,
    error TEXT
);

CREATE TABLE IF NOT EXISTS business_records (
    id TEXT PRIMARY KEY,
    job_id TEXT NOT NULL,
    business_name TEXT NOT NULL,
    address TEXT,
    phone TEXT DEFAULT '[]',
    email TEXT DEFAULT '[]',
    website TEXT,
    working_hours TEXT,
    rating REAL,
    review_count INTEGER,
    services TEXT DEFAULT '[]',
    specialties TEXT DEFAULT '[]',
    license_information TEXT,
    certifications TEXT DEFAULT '[]',
    awards TEXT DEFAULT '[]',
    social_profiles TEXT DEFAULT '{}',
    image_urls TEXT DEFAULT '[]',
    source_urls TEXT DEFAULT '{}',
    verification_status TEXT DEFAULT 'unverified',
    verification_details TEXT DEFAULT '{}',
    source_reliability_score REAL DEFAULT 0.0,
    rank_score REAL DEFAULT 0.0,
    raw_sources TEXT DEFAULT '[]',
    discovered_at TEXT NOT NULL,
    last_updated TEXT NOT NULL,
    FOREIGN KEY (job_id) REFERENCES research_jobs(id)
);

CREATE INDEX IF NOT EXISTS idx_business_job_id ON business_records(job_id);
CREATE INDEX IF NOT EXISTS idx_business_name_address ON business_records(business_name, address);
CREATE INDEX IF NOT EXISTS idx_jobs_query ON research_jobs(query);
CREATE INDEX IF NOT EXISTS idx_jobs_created_at ON research_jobs(created_at);
"""


class Database:
    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        self._db_path = self.settings.sqlite_path
        self._connection: aiosqlite.Connection | None = None

    async def connect(self) -> None:
        db_dir = os.path.dirname(self._db_path)
        if db_dir:
            os.makedirs(db_dir, exist_ok=True)
        self._connection = await aiosqlite.connect(self._db_path)
        self._connection.row_factory = aiosqlite.Row
        await self._connection.execute("PRAGMA journal_mode=WAL")
        await self._connection.execute("PRAGMA foreign_keys=ON")
        await self._connection.executescript(SCHEMA)
        await self._migrate_schema()
        await self._connection.commit()
        logger.info("Database connected: %s", self._db_path)

    async def _migrate_schema(self) -> None:
        """Add columns introduced after initial schema."""
        cursor = await self.conn.execute("PRAGMA table_info(business_records)")
        cols = {row[1] for row in await cursor.fetchall()}
        if "rank_score" not in cols:
            await self.conn.execute(
                "ALTER TABLE business_records ADD COLUMN rank_score REAL DEFAULT 0.0"
            )

    async def close(self) -> None:
        if self._connection:
            await self._connection.close()
            self._connection = None

    @property
    def conn(self) -> aiosqlite.Connection:
        if self._connection is None:
            raise RuntimeError("Database not connected")
        return self._connection

    async def create_job(self, job: ResearchJob) -> str:
        await self.conn.execute(
            """
            INSERT INTO research_jobs (
                id, query, category, location, status, progress_pct,
                businesses_found, businesses_verified, duplicates_removed,
                sources_searched, duration_seconds, llm_provider,
                created_at, completed_at, error
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                job.id,
                job.query,
                job.category,
                job.location,
                job.status,
                job.progress_pct,
                job.businesses_found,
                job.businesses_verified,
                job.duplicates_removed,
                job.sources_searched,
                job.duration_seconds,
                job.llm_provider,
                job.created_at.isoformat(),
                job.completed_at.isoformat() if job.completed_at else None,
                job.error,
            ),
        )
        await self.conn.commit()
        return job.id

    async def update_job(self, job_id: str, **fields: Any) -> None:
        if not fields:
            return
        allowed = {
            "category", "location", "status", "progress_pct",
            "businesses_found", "businesses_verified", "duplicates_removed",
            "sources_searched", "duration_seconds", "llm_provider",
            "completed_at", "error",
        }
        updates = []
        values: list[Any] = []
        for key, value in fields.items():
            if key not in allowed:
                continue
            if isinstance(value, datetime):
                value = value.isoformat()
            updates.append(f"{key} = ?")
            values.append(value)
        if not updates:
            return
        values.append(job_id)
        await self.conn.execute(
            f"UPDATE research_jobs SET {', '.join(updates)} WHERE id = ?",
            values,
        )
        await self.conn.commit()

    async def get_job(self, job_id: str) -> ResearchJob | None:
        cursor = await self.conn.execute(
            "SELECT * FROM research_jobs WHERE id = ?", (job_id,)
        )
        row = await cursor.fetchone()
        if not row:
            return None
        return self._row_to_job(dict(row))

    async def get_all_jobs(self) -> list[ResearchJob]:
        cursor = await self.conn.execute(
            "SELECT * FROM research_jobs ORDER BY created_at DESC"
        )
        rows = await cursor.fetchall()
        return [self._row_to_job(dict(r)) for r in rows]

    async def check_cache(self, query: str) -> str | None:
        cutoff = (
            datetime.now(timezone.utc)
            - timedelta(hours=self.settings.cache_ttl_hours)
        ).isoformat()
        cursor = await self.conn.execute(
            """
            SELECT id FROM research_jobs
            WHERE query = ? AND status = 'complete' AND created_at >= ?
            ORDER BY created_at DESC LIMIT 1
            """,
            (query.strip(), cutoff),
        )
        row = await cursor.fetchone()
        return row["id"] if row else None

    async def upsert_business(self, business: BusinessRecord) -> BusinessRecord:
        business.last_updated = utcnow()
        await self.conn.execute(
            """
            INSERT INTO business_records (
                id, job_id, business_name, address, phone, email, website,
                working_hours, rating, review_count, services, specialties,
                license_information, certifications, awards, social_profiles,
                image_urls,                 source_urls, verification_status, verification_details,
                source_reliability_score, rank_score, raw_sources, discovered_at, last_updated
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                business_name=excluded.business_name,
                address=excluded.address,
                phone=excluded.phone,
                email=excluded.email,
                website=excluded.website,
                working_hours=excluded.working_hours,
                rating=excluded.rating,
                review_count=excluded.review_count,
                services=excluded.services,
                specialties=excluded.specialties,
                license_information=excluded.license_information,
                certifications=excluded.certifications,
                awards=excluded.awards,
                social_profiles=excluded.social_profiles,
                image_urls=excluded.image_urls,
                source_urls=excluded.source_urls,
                verification_status=excluded.verification_status,
                verification_details=excluded.verification_details,
                source_reliability_score=excluded.source_reliability_score,
                rank_score=excluded.rank_score,
                raw_sources=excluded.raw_sources,
                last_updated=excluded.last_updated
            """,
            self._business_to_row(business),
        )
        await self.conn.commit()
        return business

    async def batch_upsert_businesses(
        self, businesses: list[BusinessRecord]
    ) -> None:
        for business in businesses:
            await self.upsert_business(business)

    async def get_businesses_by_job(
        self,
        job_id: str,
        page: int = 1,
        page_size: int = 100,
        search: str | None = None,
        sort_by: str = "rank_score",
        sort_order: str = "desc",
        verification_status: str | None = None,
    ) -> tuple[list[BusinessRecord], int]:
        allowed_sort = {
            "business_name", "address", "rating", "verification_status",
            "source_reliability_score", "rank_score", "discovered_at",
        }
        if sort_by not in allowed_sort:
            sort_by = "business_name"
        order = "DESC" if sort_order.lower() == "desc" else "ASC"

        conditions = ["job_id = ?"]
        params: list[Any] = [job_id]

        if search:
            conditions.append(
                "(business_name LIKE ? OR address LIKE ? OR website LIKE ?)"
            )
            pattern = f"%{search}%"
            params.extend([pattern, pattern, pattern])

        if verification_status:
            conditions.append("verification_status = ?")
            params.append(verification_status)

        where = " AND ".join(conditions)

        count_cursor = await self.conn.execute(
            f"SELECT COUNT(*) as cnt FROM business_records WHERE {where}",
            params,
        )
        count_row = await count_cursor.fetchone()
        total = count_row["cnt"] if count_row else 0

        offset = (page - 1) * page_size
        cursor = await self.conn.execute(
            f"""
            SELECT * FROM business_records WHERE {where}
            ORDER BY {sort_by} {order}
            LIMIT ? OFFSET ?
            """,
            params + [page_size, offset],
        )
        rows = await cursor.fetchall()
        return [self._row_to_business(dict(r)) for r in rows], total

    def _business_to_row(self, b: BusinessRecord) -> tuple[Any, ...]:
        return (
            b.id,
            b.job_id,
            b.business_name,
            b.address,
            json.dumps(b.phone),
            json.dumps(b.email),
            b.website,
            json.dumps(b.working_hours) if b.working_hours else None,
            b.rating,
            b.review_count,
            json.dumps(b.services),
            json.dumps(b.specialties),
            b.license_information,
            json.dumps(b.certifications),
            json.dumps(b.awards),
            json.dumps(b.social_profiles),
            json.dumps(b.image_urls),
            json.dumps(b.source_urls),
            b.verification_status,
            json.dumps(b.verification_details),
            b.source_reliability_score,
            b.rank_score,
            json.dumps(b.raw_sources),
            b.discovered_at.isoformat(),
            b.last_updated.isoformat(),
        )

    def _row_to_business(self, row: dict[str, Any]) -> BusinessRecord:
        return BusinessRecord(
            id=row["id"],
            job_id=row["job_id"],
            business_name=row["business_name"],
            address=row["address"],
            phone=json.loads(row["phone"] or "[]"),
            email=json.loads(row["email"] or "[]"),
            website=row["website"],
            working_hours=json.loads(row["working_hours"]) if row["working_hours"] else None,
            rating=row["rating"],
            review_count=row["review_count"],
            services=json.loads(row["services"] or "[]"),
            specialties=json.loads(row["specialties"] or "[]"),
            license_information=row["license_information"],
            certifications=json.loads(row["certifications"] or "[]"),
            awards=json.loads(row["awards"] or "[]"),
            social_profiles=json.loads(row["social_profiles"] or "{}"),
            image_urls=json.loads(row["image_urls"] or "[]"),
            source_urls=json.loads(row["source_urls"] or "{}"),
            verification_status=row["verification_status"],
            verification_details=json.loads(row["verification_details"] or "{}"),
            source_reliability_score=row["source_reliability_score"] or 0.0,
            rank_score=row["rank_score"] or 0.0,
            raw_sources=json.loads(row["raw_sources"] or "[]"),
            discovered_at=datetime.fromisoformat(row["discovered_at"]),
            last_updated=datetime.fromisoformat(row["last_updated"]),
        )

    def _row_to_job(self, row: dict[str, Any]) -> ResearchJob:
        return ResearchJob(
            id=row["id"],
            query=row["query"],
            category=row["category"] or "",
            location=row["location"] or "",
            status=row["status"],
            progress_pct=row["progress_pct"] or 0.0,
            businesses_found=row["businesses_found"] or 0,
            businesses_verified=row["businesses_verified"] or 0,
            duplicates_removed=row["duplicates_removed"] or 0,
            sources_searched=row["sources_searched"] or 0,
            duration_seconds=row["duration_seconds"],
            llm_provider=row["llm_provider"] or "auto",
            created_at=datetime.fromisoformat(row["created_at"]),
            completed_at=(
                datetime.fromisoformat(row["completed_at"])
                if row["completed_at"]
                else None
            ),
            error=row["error"],
        )


_db_instance: Database | None = None


async def get_database() -> Database:
    global _db_instance
    if _db_instance is None:
        _db_instance = Database()
        await _db_instance.connect()
    return _db_instance
