from __future__ import annotations

import datetime
import hashlib
import hmac
from jose import JWTError, jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from database import get_db
from sqlalchemy.orm import Session
from models import Teacher, Student
from config import JWT_SECRET_KEY

SECRET_KEY = JWT_SECRET_KEY
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_DAYS = 30
STUDENT_TOKEN_VERSION = 2

security = HTTPBearer()


def create_access_token(data: dict) -> str:
    if not SECRET_KEY:
        raise RuntimeError("JWT_SECRET_KEY must be configured")
    to_encode = data.copy()
    expire = datetime.datetime.utcnow() + datetime.timedelta(days=ACCESS_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def verify_token(token: str) -> dict:
    if not SECRET_KEY:
        raise HTTPException(status_code=503, detail="认证服务尚未配置")
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效的登录凭证",
        )


def teacher_token_version(password_hash: str | None) -> str:
    """Bind a teacher token to the current password without exposing the hash."""
    return hmac.new(
        SECRET_KEY.encode(), (password_hash or "").encode(), hashlib.sha256
    ).hexdigest()


def get_current_teacher(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
) -> dict:
    payload = verify_token(credentials.credentials)
    if payload.get("role") != "teacher":
        raise HTTPException(status_code=401, detail="需要教师身份")
    try:
        teacher_id = int(payload["sub"])
    except (KeyError, ValueError, TypeError):
        raise HTTPException(status_code=401, detail="无效的登录凭证") from None
    teacher = db.get(Teacher, teacher_id)
    if not teacher or not teacher.authorized:
        raise HTTPException(status_code=401, detail="教师账号不可用")
    if not hmac.compare_digest(
        payload.get("password_version", ""),
        teacher_token_version(teacher.password_hash),
    ):
        raise HTTPException(status_code=401, detail="登录凭证已失效，请重新登录")
    return payload


def create_student_token(student_id: int, team_id: int, password_hash: str) -> str:
    return create_access_token({
        "sub": str(student_id),
        "role": "student",
        "team_id": str(team_id),
        "password_version": teacher_token_version(password_hash),
        "auth_version": STUDENT_TOKEN_VERSION,
    })


def get_current_student(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
) -> dict:
    payload = verify_token(credentials.credentials)
    if payload.get("role") != "student":
        raise HTTPException(status_code=401, detail="需要学生身份")
    if payload.get("auth_version") != STUDENT_TOKEN_VERSION:
        raise HTTPException(status_code=401, detail="登录凭证已失效，请重新登录")
    try:
        student_id = int(payload["sub"])
    except (KeyError, ValueError, TypeError):
        raise HTTPException(status_code=401, detail="无效的登录凭证") from None
    student = db.get(Student, student_id)
    if not student:
        raise HTTPException(status_code=404, detail="学生不存在")
    if not student.pin_hash or not hmac.compare_digest(
        payload.get("password_version", ""),
        teacher_token_version(student.pin_hash),
    ):
        raise HTTPException(status_code=401, detail="登录凭证已失效，请重新登录")
    if str(student.team_id) != payload.get("team_id"):
        raise HTTPException(status_code=401, detail="学生所属小组已变更，请重新登录")
    return {
        "student_id": student.id,
        "team_id": student.team_id,
        "name": student.name,
        "must_change_password": student.must_change_password,
    }


def get_current_active_student(student: dict = Depends(get_current_student)) -> dict:
    if student["must_change_password"]:
        raise HTTPException(status_code=403, detail="请先修改初始密码")
    return student
