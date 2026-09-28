from __future__ import annotations

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import asc, desc, func, or_, select
from sqlalchemy.orm import Session

from lead_factory.api.dependencies import get_session
from lead_factory.api.errors import ApiError
from lead_factory.models import Account, LeadGrade, ReviewDecision, ReviewStatus
from lead_factory.schemas import AccountSummary, ReviewDecisionCreate

router = APIRouter(prefix="/accounts", tags=["accounts"])


@router.get("")
def list_accounts(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=100),
    search: str | None = None,
    country: str | None = None,
    icp: str | None = None,
    grade: LeadGrade | None = None,
    review_status: ReviewStatus | None = None,
    sort: str = Query(default="created_desc", pattern="^(created_desc|score_desc|score_asc|name_asc)$"),
    session: Session = Depends(get_session),
) -> dict[str, object]:
    filters = []
    if search:
        pattern = f"%{search}%"
        filters.append(or_(Account.display_name.ilike(pattern), Account.normalized_domain.ilike(pattern)))
    if country:
        filters.append(Account.country == country)
    if icp:
        filters.append(Account.industry == icp)
    if grade:
        filters.append(Account.grade == grade)
    if review_status:
        filters.append(Account.review_status == review_status)
    order = {
        "created_desc": desc(Account.created_at),
        "score_desc": desc(Account.score),
        "score_asc": asc(Account.score),
        "name_asc": asc(Account.display_name),
    }[sort]
    total = session.scalar(select(func.count()).select_from(Account).where(*filters)) or 0
    accounts = session.scalars(
        select(Account).where(*filters).order_by(order).offset((page - 1) * page_size).limit(page_size)
    ).all()
    return {
        "items": [AccountSummary.model_validate(account).model_dump(mode="json") for account in accounts],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


def _get_account(session: Session, account_id: str) -> Account:
    account = session.get(Account, account_id)
    if account is None:
        raise ApiError(404, "account_not_found", "Account was not found")
    return account


@router.get("/{account_id}")
def account_detail(account_id: str, session: Session = Depends(get_session)) -> dict[str, object]:
    account = _get_account(session, account_id)
    return {
        **AccountSummary.model_validate(account).model_dump(mode="json"),
        "description": account.description,
        "industry": account.industry,
        "scale_signals": account.scale_signals,
        "contact_routes": account.contact_routes,
        "confidence": account.confidence,
        "calculation_version": account.calculation_version,
        "evidence": [
            {
                "id": item.id,
                "signal_type": item.signal_type,
                "excerpt": item.excerpt,
                "source_url": item.source_url,
                "confidence": item.confidence,
            }
            for item in account.evidence
        ],
        "score_breakdown": [
            {
                "rule_id": item.rule_id,
                "dimension": item.dimension,
                "points": item.points,
                "excerpt": item.excerpt,
                "source_url": item.source_url,
            }
            for item in account.score_breakdowns
        ],
        "product_matches": [
            {
                "family_id": item.family_id,
                "recommended_products": item.recommended_products,
                "reason": item.reason,
                "confidence": item.confidence,
                "evidence_ids": item.evidence_ids,
            }
            for item in account.product_matches
        ],
        "review_history": [
            {
                "id": item.id,
                "status": item.status.value,
                "note": item.note,
                "actor": item.actor,
                "created_at": item.created_at.isoformat(),
            }
            for item in account.review_decisions
        ],
    }


@router.post("/{account_id}/review", status_code=status.HTTP_201_CREATED)
def review_account(
    account_id: str,
    body: ReviewDecisionCreate,
    session: Session = Depends(get_session),
) -> dict[str, object]:
    account = _get_account(session, account_id)
    decision = ReviewDecision(account=account, status=body.status, note=body.note, actor=body.actor)
    account.review_status = body.status
    session.add(decision)
    session.commit()
    session.refresh(decision)
    return {
        "id": decision.id,
        "status": decision.status.value,
        "note": decision.note,
        "actor": decision.actor,
        "created_at": decision.created_at.isoformat(),
    }
