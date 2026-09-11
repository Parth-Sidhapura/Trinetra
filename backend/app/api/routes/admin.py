"""Role management + demo seeding."""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.security import CurrentUser, require_role
from app.db.session import get_db
from app.models import UserProfile
from app.services.audit import write_audit
from app.services.llm import provider_info

router = APIRouter(prefix="/admin", tags=["admin"])


class RoleUpdate(BaseModel):
    email: str
    role: str
    clearance: str = "confidential"


@router.get("/me")
def me(user: CurrentUser):
    return {"user_id": user.user_id, "email": user.email, "role": user.role,
            "department": user.department, "clearance": user.clearance}


@router.get("/users")
def list_users(user: CurrentUser, db: Session = Depends(get_db),
               _=Depends(require_role("ADMIN"))):
    return [{"id": str(u.id), "email": u.email, "role": u.role,
             "department": u.department, "clearance": u.clearance}
            for u in db.query(UserProfile).all()]


@router.post("/users/role")
def set_role(body: RoleUpdate, user: CurrentUser, db: Session = Depends(get_db),
             _=Depends(require_role("ADMIN"))):
    if body.role not in ("CONSTABLE", "INSPECTOR", "ADMIN"):
        raise HTTPException(400, "Invalid role")
    profile = db.query(UserProfile).filter(UserProfile.email == body.email).first()
    if profile is None:
        raise HTTPException(404, "User not found — they must sign in once first")
    profile.role = body.role
    profile.clearance = body.clearance
    db.commit()
    write_audit(db, actor=user.email, actor_role=user.role,
                action="admin.set_role", resource=f"user:{body.email}",
                detail={"new_role": body.role})
    return {"email": profile.email, "role": profile.role,
            "clearance": profile.clearance}


@router.get("/system")
def system_info(user: CurrentUser, db: Session = Depends(get_db)):
    from app.core.config import settings
    return {
        "env": settings.ENV,
        "llm": provider_info(),
        "neo4j_enabled": settings.NEO4J_ENABLED,
        "celery_enabled": settings.CELERY_ENABLED,
        "whisper_enabled": settings.WHISPER_ENABLED,
        "clamav_enabled": settings.CLAMAV_ENABLED,
        "graph_caps": {"max_nodes": settings.MAX_GRAPH_NODES,
                       "max_edges": settings.MAX_GRAPH_EDGES},
    }
