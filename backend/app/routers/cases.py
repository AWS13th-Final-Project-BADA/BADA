"""사건 CRUD. 인증은 공통 deps.get_current_user seam 사용."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..db import get_db
from ..deps import get_current_user
from ..models import Case, User
from ..schemas import CaseCreate

router = APIRouter(prefix="/cases", tags=["cases"])


def _dict(c: Case) -> dict:
    return {
        "id": c.id,
        "workplace_name": c.workplace_name,
        "employer_name": c.employer_name,
        "work_start_date": str(c.work_start_date) if c.work_start_date else None,
        "work_end_date": str(c.work_end_date) if c.work_end_date else None,
        "agreed_hourly_wage": c.agreed_hourly_wage,
        "agreed_weekly_hours": float(c.agreed_weekly_hours) if c.agreed_weekly_hours is not None else None,
        "issue_types": c.issue_types or [],
        "status": c.status,
    }


@router.post("")
def create_case(payload: CaseCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    from ..middleware.prometheus import CASES_CREATED
    case = Case(user_id=user.id, **payload.model_dump())
    db.add(case); db.commit(); db.refresh(case)
    CASES_CREATED.inc()
    return _dict(case)


@router.get("")
def list_cases(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    rows = db.query(Case).filter(Case.user_id == user.id).order_by(Case.created_at.desc()).all()
    return [_dict(c) for c in rows]


@router.get("/{case_id}")
def get_case(case_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    c = db.get(Case, case_id)
    if not c:
        raise HTTPException(404, "case not found")
    if c.user_id != user.id:
        raise HTTPException(403, "이 사건에 접근할 권한이 없습니다")
    return _dict(c)
