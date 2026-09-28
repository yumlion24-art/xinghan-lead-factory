from __future__ import annotations

from fastapi import APIRouter, Depends, Request, status
from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from lead_factory.api.dependencies import get_session
from lead_factory.api.errors import ApiError
from lead_factory.models import Account, SearchTask, SearchTaskAccount
from lead_factory.schemas import SearchTaskCreate, SearchTaskSummary

router = APIRouter(prefix="/search-tasks", tags=["search-tasks"])


@router.get("")
def list_tasks(session: Session = Depends(get_session)) -> dict[str, object]:
    tasks = session.scalars(select(SearchTask).order_by(desc(SearchTask.created_at)).limit(100)).all()
    return {"items": [SearchTaskSummary.model_validate(task).model_dump(mode="json") for task in tasks]}


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_task(
    body: SearchTaskCreate,
    request: Request,
    session: Session = Depends(get_session),
) -> dict[str, object]:
    if not body.query.strip() and not body.seed_urls:
        raise ApiError(422, "search_criteria_required", "Provide a query or at least one seed URL")
    task = SearchTask(
        query=body.query.strip(),
        countries=body.countries,
        icp_ids=body.icp_ids,
        seed_urls=[str(url) for url in body.seed_urls],
        limits={
            "max_results": body.max_results,
            "max_pages_per_domain": body.max_pages_per_domain,
        },
    )
    session.add(task)
    session.commit()
    session.refresh(task)
    request.app.state.runner.enqueue(task.id)
    return SearchTaskSummary.model_validate(task).model_dump(mode="json")


def _get_task(session: Session, task_id: str) -> SearchTask:
    task = session.get(SearchTask, task_id)
    if task is None:
        raise ApiError(404, "search_task_not_found", "Search task was not found")
    return task


@router.get("/{task_id}")
def task_detail(task_id: str, session: Session = Depends(get_session)) -> dict[str, object]:
    task = _get_task(session, task_id)
    accounts = session.scalars(
        select(Account)
        .join(SearchTaskAccount, SearchTaskAccount.account_id == Account.id)
        .where(SearchTaskAccount.search_task_id == task_id)
    ).all()
    return {
        **SearchTaskSummary.model_validate(task).model_dump(mode="json"),
        "accounts": [
            {"id": account.id, "display_name": account.display_name, "grade": account.grade}
            for account in accounts
        ],
    }


@router.post("/{task_id}/cancel", status_code=status.HTTP_202_ACCEPTED)
def cancel_task(
    task_id: str,
    request: Request,
    session: Session = Depends(get_session),
) -> dict[str, str]:
    _get_task(session, task_id)
    request.app.state.runner.cancel(task_id)
    return {"status": "cancellation_requested"}
