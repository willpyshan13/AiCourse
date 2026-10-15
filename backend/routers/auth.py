from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Response, Request
from sqlalchemy import or_
from sqlalchemy.orm import Session
from database import get_db
from models import Teacher, Student, Team, Class_
from schemas import WeChatLoginRequest, TokenResponse, TeacherInfo, StudentLoginRequest, StudentTokenResponse, StudentPasswordChange
from auth import create_access_token, get_current_teacher, get_current_student, create_student_token, teacher_token_version
from passwords import hash_password, verify_password
from student_passwords import default_student_password, verify_student_password

router = APIRouter(prefix="/api/auth", tags=["认证"])


@router.post("/login", response_model=TokenResponse)
def wechat_login(req: WeChatLoginRequest, response: Response, request: Request, db: Session = Depends(get_db)):
    """Password login for an administrator-provisioned teacher account."""
    if not req.name.strip() or not req.password:
        raise HTTPException(status_code=401, detail="姓名或密码错误")
    matches = db.query(Teacher).filter(Teacher.name == req.name.strip()).all()
    if len(matches) != 1 or not matches[0].password_hash:
        raise HTTPException(status_code=401, detail="姓名或密码错误")
    teacher = matches[0]
    if not teacher.authorized or not verify_password(req.password, teacher.password_hash):
        raise HTTPException(status_code=401, detail="姓名或密码错误")
    token = create_access_token({
        "sub": str(teacher.id),
        "role": "teacher",
        "password_version": teacher_token_version(teacher.password_hash),
    })
    response.set_cookie(
        "teacher_media", token, max_age=30 * 24 * 3600, httponly=True,
        secure=request.url.scheme == "https", samesite="strict", path="/uploads/practices",
    )
    return TokenResponse(
        access_token=token,
        teacher_id=teacher.id,
        name=teacher.name,
        school=teacher.school or "",
    )


@router.post("/logout")
def logout(response: Response):
    response.delete_cookie("teacher_media", path="/uploads/practices")
    return {"ok": True}


@router.get("/me", response_model=TeacherInfo)
def get_me(
    payload: dict = Depends(get_current_teacher),
    db: Session = Depends(get_db),
):
    teacher = db.query(Teacher).filter(Teacher.id == int(payload["sub"])).first()
    if not teacher:
        raise HTTPException(status_code=404, detail="教师不存在")
    return teacher


@router.post("/student-login", response_model=StudentTokenResponse)
def student_login(
    req: StudentLoginRequest, response: Response, request: Request,
    db: Session = Depends(get_db),
) -> StudentTokenResponse:
    """Log in with a student number or a family phone number within a team."""
    team = db.query(Team).filter(Team.id == req.team_id).first()
    if not team:
        raise HTTPException(status_code=404, detail="小组不存在")

    identifier = req.identifier.strip()
    if not identifier or not req.password:
        raise HTTPException(status_code=401, detail="学号或手机号、密码错误")
    students = db.query(Student).filter(
        Student.team_id == req.team_id,
        or_(Student.student_no == identifier, Student.phone == identifier),
    ).all()
    matches = [
        student for student in students
        if verify_student_password(student, req.password)
    ]
    if len(matches) != 1:
        if len(matches) > 1:
            detail = (
                "同组多人共用此手机号，请改用学号登录"
                if all(student.phone == identifier for student in matches)
                else "学号重复，请联系老师核对"
            )
            raise HTTPException(status_code=409, detail=detail)
        raise HTTPException(status_code=401, detail="学号或手机号、密码错误")
    student = matches[0]
    initial_password = default_student_password(student.phone)
    if not student.pin_hash:
        student.pin_hash = hash_password(req.password)
    if initial_password == req.password:
        student.must_change_password = True
    if db.is_modified(student):
        db.commit()

    token = create_student_token(student.id, team.id, student.pin_hash)
    response.set_cookie(
        "student_media", token, max_age=30 * 24 * 3600, httponly=True,
        secure=request.url.scheme == "https", samesite="strict", path="/uploads/practices",
    )
    return StudentTokenResponse(
        access_token=token,
        student_id=student.id,
        name=student.name,
        team_id=team.id,
        team_name=team.name,
        class_name=team.class_.name,
        must_change_password=student.must_change_password,
    )


@router.post("/student-password")
def change_student_password(
    body: StudentPasswordChange,
    response: Response,
    request: Request,
    student: dict = Depends(get_current_student),
    db: Session = Depends(get_db),
) -> dict:
    account = db.get(Student, student["student_id"])
    if not verify_password(body.current_password, account.pin_hash):
        raise HTTPException(status_code=400, detail="当前密码错误")
    if len(body.new_password) < 8:
        raise HTTPException(status_code=400, detail="新密码至少需要8位")
    account.pin_hash = hash_password(body.new_password)
    account.must_change_password = False
    db.commit()
    token = create_student_token(account.id, account.team_id, account.pin_hash)
    response.set_cookie(
        "student_media", token, max_age=30 * 24 * 3600, httponly=True,
        secure=request.url.scheme == "https", samesite="strict", path="/uploads/practices",
    )
    return {
        "access_token": token,
        "student_id": account.id,
        "team_id": account.team_id,
        "name": account.name,
        "must_change_password": False,
    }


@router.get("/student-me")
def get_student_me(student: dict = Depends(get_current_student)) -> dict:
    return student


@router.post("/student-logout")
def student_logout(response: Response) -> dict:
    response.delete_cookie("student_media", path="/uploads/practices")
    return {"ok": True}
