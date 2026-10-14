"""Administrator-only teacher management."""
from __future__ import annotations

import hmac

from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel
from sqlalchemy.orm import Session

from add_teacher import create_teacher
from auth import create_access_token, verify_token
from config import ADMIN_PASSWORD, ADMIN_USERNAME
from database import get_db
from models import Teacher

router = APIRouter(prefix="/api/admin", tags=["管理员"])
bearer = HTTPBearer()


class AdminLogin(BaseModel):
    username: str
    password: str


class TeacherCreate(BaseModel):
    name: str
    school: str = ""
    password: str


def require_admin(credentials: HTTPAuthorizationCredentials = Depends(bearer)) -> None:
    payload = verify_token(credentials.credentials)
    if payload.get("role") != "admin":
        raise HTTPException(status_code=403, detail="需要管理员身份")


@router.post("/login")
def login(body: AdminLogin):
    if not ADMIN_USERNAME or len(ADMIN_PASSWORD) < 12:
        raise HTTPException(status_code=503, detail="管理员账号尚未配置")
    if not (
        hmac.compare_digest(body.username, ADMIN_USERNAME)
        and hmac.compare_digest(body.password, ADMIN_PASSWORD)
    ):
        raise HTTPException(status_code=401, detail="管理员账号或密码错误")
    return {"access_token": create_access_token({"sub": "admin", "role": "admin"})}


@router.get("/teachers", dependencies=[Depends(require_admin)])
def list_teachers(db: Session = Depends(get_db)):
    teachers = db.query(Teacher).order_by(Teacher.id).all()
    return [{"id": teacher.id, "name": teacher.name, "school": teacher.school or ""} for teacher in teachers]


@router.post("/teachers", dependencies=[Depends(require_admin)])
def add_teacher(body: TeacherCreate, db: Session = Depends(get_db)):
    try:
        teacher = create_teacher(db, body.name, body.school, body.password)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from None
    return {"id": teacher.id, "name": teacher.name, "school": teacher.school or ""}
