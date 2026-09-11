from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.security import CurrentUser, authorize_case
from app.db.session import get_db
from app.services.audit import write_audit
from app.services.copilot import ask

router = APIRouter(prefix="/cases/{case_id}/copilot", tags=["copilot"])


class Question(BaseModel):
    question: str


@router.post("")
def ask_copilot(case_id: str, body: Question, user: CurrentUser,
                db: Session = Depends(get_db)):
    """Authorization happens BEFORE retrieval - authorize_case() runs first,
    so the query planner only ever sees data this user may already see."""
    authorize_case(db, user, case_id)
    result = ask(db, case_id, body.question)
    write_audit(db, actor=user.email, actor_role=user.role,
                action="copilot.query", case_id=case_id,
                detail={"question": body.question[:300],
                        "blocked": result["blocked"],
                        "grounded": result["grounded"]})
    return result
