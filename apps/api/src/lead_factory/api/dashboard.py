from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from lead_factory.api.dependencies import get_session
from lead_factory.models import Account, LeadGrade, SearchTask, SearchTaskStatus

router = APIRouter(tags=["dashboard"])


@router.get("/dashboard")
def dashboard(session: Session = Depends(get_session)) -> dict[str, object]:
    total = session.scalar(select(func.count()).select_from(Account)) or 0
    grades = {
        grade.value: session.scalar(select(func.count()).select_from(Account).where(Account.grade == grade)) or 0
        for grade in LeadGrade
    }
    review_counts = {
        status: count
        for status, count in session.execute(
            select(Account.review_status, func.count()).group_by(Account.review_status)
        )
    }
    active_tasks = session.scalar(
        select(func.count()).select_from(SearchTask).where(
            SearchTask.status.in_([SearchTaskStatus.QUEUED, SearchTaskStatus.RUNNING])
        )
    ) or 0
    return {
        "accounts_total": total,
        "grades": grades,
        "reviews": {getattr(key, "value", str(key)): value for key, value in review_counts.items()},
        "active_tasks": active_tasks,
        "budget_usage": {"pages": 0, "domains": 0, "ai_calls": 0},
    }

