from __future__ import annotations

import enum
import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import JSON, Boolean, DateTime, Enum, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from lead_factory.db import Base


def utc_now() -> datetime:
    return datetime.now(UTC)


def uuid_string() -> str:
    return str(uuid.uuid4())


class ReviewStatus(str, enum.Enum):
    NEEDS_REVIEW = "needs_review"
    APPROVED = "approved"
    REJECTED = "rejected"


class LeadGrade(str, enum.Enum):
    A = "A"
    B = "B"
    C = "C"


class SearchTaskStatus(str, enum.Enum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    PARTIALLY_COMPLETED = "partially_completed"
    CANCELLED = "cancelled"
    FAILED = "failed"


class Account(Base):
    __tablename__ = "accounts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_string)
    display_name: Mapped[str] = mapped_column(String(255))
    normalized_domain: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    website_url: Mapped[str | None] = mapped_column(String(2048))
    country: Mapped[str | None] = mapped_column(String(120), index=True)
    industry: Mapped[str | None] = mapped_column(String(255))
    company_type: Mapped[str | None] = mapped_column(String(255))
    description: Mapped[str | None] = mapped_column(Text)
    scale_signals: Mapped[list[str]] = mapped_column(JSON, default=list)
    contact_routes: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)
    review_status: Mapped[ReviewStatus] = mapped_column(
        Enum(ReviewStatus, native_enum=False), default=ReviewStatus.NEEDS_REVIEW, index=True
    )
    grade: Mapped[LeadGrade | None] = mapped_column(Enum(LeadGrade, native_enum=False), index=True)
    score: Mapped[int] = mapped_column(Integer, default=0, index=True)
    confidence: Mapped[float] = mapped_column(Float, default=0.0)
    calculation_version: Mapped[str | None] = mapped_column(String(80))
    enrichment_mode: Mapped[str] = mapped_column(String(30), default="rules_only")
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now
    )

    source_pages: Mapped[list["SourcePage"]] = relationship(back_populates="account")
    evidence: Mapped[list["Evidence"]] = relationship(back_populates="account")
    score_breakdowns: Mapped[list["ScoreBreakdown"]] = relationship(back_populates="account")
    product_matches: Mapped[list["ProductMatch"]] = relationship(back_populates="account")
    review_decisions: Mapped[list["ReviewDecision"]] = relationship(
        back_populates="account", order_by="ReviewDecision.created_at"
    )


class SearchTask(Base):
    __tablename__ = "search_tasks"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_string)
    query: Mapped[str] = mapped_column(String(500), default="")
    countries: Mapped[list[str]] = mapped_column(JSON, default=list)
    icp_ids: Mapped[list[str]] = mapped_column(JSON, default=list)
    seed_urls: Mapped[list[str]] = mapped_column(JSON, default=list)
    limits: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    status: Mapped[SearchTaskStatus] = mapped_column(
        Enum(SearchTaskStatus, native_enum=False), default=SearchTaskStatus.QUEUED, index=True
    )
    progress: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    budget_usage: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    failure_summary: Mapped[str | None] = mapped_column(Text)
    cancel_requested: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class SourcePage(Base):
    __tablename__ = "source_pages"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_string)
    account_id: Mapped[str | None] = mapped_column(ForeignKey("accounts.id", ondelete="CASCADE"), index=True)
    search_task_id: Mapped[str | None] = mapped_column(ForeignKey("search_tasks.id"), index=True)
    url: Mapped[str] = mapped_column(String(2048))
    canonical_url: Mapped[str] = mapped_column(String(2048), index=True)
    title: Mapped[str | None] = mapped_column(String(500))
    retrieval_status: Mapped[str] = mapped_column(String(80))
    content_hash: Mapped[str | None] = mapped_column(String(64), index=True)
    extracted_text: Mapped[str | None] = mapped_column(Text)
    retrieved_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    account: Mapped[Account | None] = relationship(back_populates="source_pages")
    evidence: Mapped[list["Evidence"]] = relationship(back_populates="source_page")


class Evidence(Base):
    __tablename__ = "evidence"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_string)
    account_id: Mapped[str] = mapped_column(ForeignKey("accounts.id", ondelete="CASCADE"), index=True)
    source_page_id: Mapped[str | None] = mapped_column(ForeignKey("source_pages.id"), index=True)
    signal_type: Mapped[str] = mapped_column(String(100), index=True)
    excerpt: Mapped[str] = mapped_column(Text)
    source_url: Mapped[str] = mapped_column(String(2048))
    confidence: Mapped[float] = mapped_column(Float, default=1.0)

    account: Mapped[Account] = relationship(back_populates="evidence")
    source_page: Mapped[SourcePage | None] = relationship(back_populates="evidence")


class ScoreBreakdown(Base):
    __tablename__ = "score_breakdowns"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_string)
    account_id: Mapped[str] = mapped_column(ForeignKey("accounts.id", ondelete="CASCADE"), index=True)
    rule_id: Mapped[str] = mapped_column(String(120))
    dimension: Mapped[str] = mapped_column(String(80))
    points: Mapped[int] = mapped_column(Integer)
    excerpt: Mapped[str | None] = mapped_column(Text)
    source_url: Mapped[str | None] = mapped_column(String(2048))
    calculation_version: Mapped[str] = mapped_column(String(80))

    account: Mapped[Account] = relationship(back_populates="score_breakdowns")


class ProductMatch(Base):
    __tablename__ = "product_matches"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_string)
    account_id: Mapped[str] = mapped_column(ForeignKey("accounts.id", ondelete="CASCADE"), index=True)
    family_id: Mapped[str] = mapped_column(String(100), index=True)
    recommended_products: Mapped[list[str]] = mapped_column(JSON, default=list)
    reason: Mapped[str] = mapped_column(Text)
    confidence: Mapped[float] = mapped_column(Float)
    evidence_ids: Mapped[list[str]] = mapped_column(JSON, default=list)

    account: Mapped[Account] = relationship(back_populates="product_matches")


class ReviewDecision(Base):
    __tablename__ = "review_decisions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_string)
    account_id: Mapped[str] = mapped_column(ForeignKey("accounts.id", ondelete="CASCADE"), index=True)
    status: Mapped[ReviewStatus] = mapped_column(Enum(ReviewStatus, native_enum=False))
    note: Mapped[str | None] = mapped_column(Text)
    actor: Mapped[str] = mapped_column(String(120), default="local_operator")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    account: Mapped[Account] = relationship(back_populates="review_decisions")

