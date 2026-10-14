from fastapi import APIRouter, Depends, HTTPException, Response, Request
from sqlalchemy.orm import Session
from database import get_db
from models import Teacher, Student, Team, Class_
from schemas import WeChatLoginRequest, TokenResponse, TeacherInfo, StudentLoginRequest, StudentTokenResponse
from auth import create_access_token, get_current_teacher, create_student_token, teacher_token_version
from passwords import verify_password

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
def student_login(req: StudentLoginRequest, db: Session = Depends(get_db)):
    """学生登录 — 输入姓名，绑定到对应小组"""
    team = db.query(Team).filter(Team.id == req.team_id).first()
    if not team:
        raise HTTPException(status_code=404, detail="小组不存在")

    students = db.query(Student).filter(
        Student.team_id == req.team_id,
        Student.name == req.name,
    ).all()
    if len(students) != 1 or not students[0].pin_hash or not verify_password(req.pin, students[0].pin_hash):
        raise HTTPException(status_code=401, detail="学生姓名或口令错误")
    student = students[0]

    token = create_student_token(student.id, team.id)
    return StudentTokenResponse(
        access_token=token,
        student_id=student.id,
        name=student.name,
        team_id=team.id,
        team_name=team.name,
        class_name=team.class_.name,
    )
