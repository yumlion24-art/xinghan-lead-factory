from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from lead_factory.api.dependencies import get_session

router = APIRouter(tags=["system"])


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/readiness")
def readiness(session: Session = Depends(get_session)) -> dict[str, str]:
    session.execute(text("SELECT 1"))
    return {"status": "ready", "database": "ok", "configuration": "ok"}

