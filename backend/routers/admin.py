"""Super administrator account and school-wide management endpoints."""
from __future__ import annotations

import hashlib
import hmac
from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel
from sqlalchemy import func, or_
from sqlalchemy.orm import Session, selectinload

from add_teacher import create_teacher
from auth import create_access_token, verify_token
from config import ADMIN_PASSWORD, ADMIN_USERNAME, JWT_SECRET_KEY
from database import get_db
from models import Class_, Evaluation, MemberRecord, Practice, Student, Teacher, Team
from passwords import hash_password
from student_passwords import reset_student_password

router = APIRouter(prefix="/api/admin", tags=["管理员"])
bearer = HTTPBearer()


class AdminLogin(BaseModel):
    username: str
    password: str


class TeacherCreate(BaseModel):
    name: str
    school: str = ""
    password: str


class TeacherUpdate(BaseModel):
    name: str
    school: str = ""
    authorized: bool


class PasswordReset(BaseModel):
    password: str


class AdminClassData(BaseModel):
    teacher_id: int
    name: str
    grade: str = ""
    description: str = ""


class AdminStudentData(BaseModel):
    class_id: int
    name: str
    student_no: str = ""
    phone: str = ""
    grade: str = ""
    birth_date: Optional[date] = None
    role: str = ""
    team_id: Optional[int] = None


def _admin_version() -> str:
    return hmac.new(
        JWT_SECRET_KEY.encode(),
        f"{ADMIN_USERNAME}:{ADMIN_PASSWORD}".encode(),
        hashlib.sha256,
    ).hexdigest()


def require_admin(credentials: HTTPAuthorizationCredentials = Depends(bearer)) -> None:
    if not ADMIN_USERNAME or len(ADMIN_PASSWORD) < 12:
        raise HTTPException(status_code=503, detail="管理员账号尚未配置")
    payload = verify_token(credentials.credentials)
    if payload.get("role") != "admin" or not hmac.compare_digest(
        payload.get("admin_version", ""), _admin_version()
    ):
        raise HTTPException(status_code=403, detail="需要管理员身份")


def _required_text(value: str, label: str, maximum: int) -> str:
    cleaned = value.strip()
    if not cleaned or len(cleaned) > maximum:
        raise HTTPException(status_code=400, detail=f"{label}不能为空且不能超过{maximum}字")
    return cleaned


def _optional_text(value: str, label: str, maximum: int) -> str:
    cleaned = value.strip()
    if len(cleaned) > maximum:
        raise HTTPException(status_code=400, detail=f"{label}不能超过{maximum}字")
    return cleaned


def _teacher(db: Session, teacher_id: int) -> Teacher:
    teacher = db.get(Teacher, teacher_id)
    if teacher is None:
        raise HTTPException(status_code=404, detail="教师不存在")
    return teacher


def _class(db: Session, class_id: int) -> Class_:
    class_ = db.get(Class_, class_id)
    if class_ is None:
        raise HTTPException(status_code=404, detail="班级不存在")
    return class_


def _student(db: Session, student_id: int) -> Student:
    student = db.get(Student, student_id)
    if student is None:
        raise HTTPException(status_code=404, detail="学生不存在")
    return student


def _class_data(db: Session, body: AdminClassData) -> tuple[Teacher, str, str, str]:
    teacher = _teacher(db, body.teacher_id)
    name = _required_text(body.name, "班级名称", 128)
    grade = _optional_text(body.grade, "年级", 32)
    description = body.description.strip()
    return teacher, name, grade, description


def _student_data(db: Session, body: AdminStudentData) -> tuple[Class_, Team | None]:
    class_ = _class(db, body.class_id)
    if body.team_id is None:
        return class_, None
    team = db.get(Team, body.team_id)
    if team is None or team.class_id != class_.id:
        raise HTTPException(status_code=400, detail="小组不属于学生班级")
    return class_, team


def _student_response(student: Student) -> dict:
    return {
        "id": student.id,
        "class_id": student.class_id,
        "team_id": student.team_id,
        "name": student.name,
        "student_no": student.student_no or "",
        "phone": student.phone or "",
        "grade": student.grade or "",
        "birth_date": student.birth_date.isoformat() if student.birth_date else None,
        "role": student.role or "",
        "team_name": student.team.name if student.team else "",
    }


@router.post("/login")
def login(body: AdminLogin) -> dict:
    if not ADMIN_USERNAME or len(ADMIN_PASSWORD) < 12:
        raise HTTPException(status_code=503, detail="管理员账号尚未配置")
    if not (
        hmac.compare_digest(body.username, ADMIN_USERNAME)
        and hmac.compare_digest(body.password, ADMIN_PASSWORD)
    ):
        raise HTTPException(status_code=401, detail="管理员账号或密码错误")
    return {"access_token": create_access_token({
        "sub": "admin", "role": "admin", "admin_version": _admin_version()
    })}


@router.get("/overview", dependencies=[Depends(require_admin)])
def overview(db: Session = Depends(get_db)) -> dict:
    return {
        "teachers": db.query(func.count(Teacher.id)).scalar(),
        "classes": db.query(func.count(Class_.id)).scalar(),
        "teams": db.query(func.count(Team.id)).scalar(),
        "students": db.query(func.count(Student.id)).scalar(),
        "practices": db.query(func.count(Practice.id)).scalar(),
    }


@router.get("/teachers", dependencies=[Depends(require_admin)])
def list_teachers(db: Session = Depends(get_db)) -> list[dict]:
    counts = dict(
        db.query(Class_.teacher_id, func.count(Class_.id)).group_by(Class_.teacher_id).all()
    )
    teachers = db.query(Teacher).order_by(Teacher.id).all()
    return [
        {
            "id": teacher.id,
            "name": teacher.name,
            "school": teacher.school or "",
            "authorized": bool(teacher.authorized),
            "class_count": counts.get(teacher.id, 0),
        }
        for teacher in teachers
    ]


@router.post("/teachers", dependencies=[Depends(require_admin)])
def add_teacher(body: TeacherCreate, db: Session = Depends(get_db)) -> dict:
    try:
        teacher = create_teacher(db, body.name, body.school, body.password)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from None
    return {"id": teacher.id, "name": teacher.name, "school": teacher.school or ""}


@router.put("/teachers/{teacher_id}", dependencies=[Depends(require_admin)])
def update_teacher(teacher_id: int, body: TeacherUpdate, db: Session = Depends(get_db)) -> dict:
    teacher = _teacher(db, teacher_id)
    name = _required_text(body.name, "教师姓名", 64)
    school = _optional_text(body.school, "学校", 128)
    duplicate = db.query(Teacher).filter(Teacher.name == name, Teacher.id != teacher_id).first()
    if duplicate:
        raise HTTPException(status_code=400, detail="教师姓名已存在")
    teacher.name = name
    teacher.school = school
    teacher.authorized = body.authorized
    db.commit()
    return {"id": teacher.id, "name": name, "school": school, "authorized": body.authorized}


@router.post("/teachers/{teacher_id}/password", dependencies=[Depends(require_admin)])
def reset_teacher_password(
    teacher_id: int, body: PasswordReset, db: Session = Depends(get_db)
) -> dict:
    if len(body.password) < 12:
        raise HTTPException(status_code=400, detail="教师密码至少12位")
    teacher = _teacher(db, teacher_id)
    teacher.password_hash = hash_password(body.password)
    db.commit()
    return {"ok": True}


@router.get("/classes", dependencies=[Depends(require_admin)])
def list_classes(db: Session = Depends(get_db)) -> list[dict]:
    classes = db.query(Class_).options(
        selectinload(Class_.teacher),
        selectinload(Class_.teams),
        selectinload(Class_.students),
    ).order_by(Class_.id).all()
    return [
        {
            "id": class_.id,
            "teacher_id": class_.teacher_id,
            "teacher_name": class_.teacher.name if class_.teacher else "",
            "name": class_.name,
            "grade": class_.grade or "",
            "description": class_.description or "",
            "team_count": len(class_.teams),
            "student_count": len(class_.students),
        }
        for class_ in classes
    ]


@router.post("/classes", dependencies=[Depends(require_admin)])
def add_class(body: AdminClassData, db: Session = Depends(get_db)) -> dict:
    _, name, grade, description = _class_data(db, body)
    class_ = Class_(teacher_id=body.teacher_id, name=name, grade=grade, description=description)
    db.add(class_)
    db.commit()
    return {"id": class_.id, "name": class_.name}


@router.put("/classes/{class_id}", dependencies=[Depends(require_admin)])
def update_class(class_id: int, body: AdminClassData, db: Session = Depends(get_db)) -> dict:
    class_ = _class(db, class_id)
    _, name, grade, description = _class_data(db, body)
    class_.teacher_id = body.teacher_id
    class_.name = name
    class_.grade = grade
    class_.description = description
    db.commit()
    return {"id": class_.id, "name": class_.name, "teacher_id": class_.teacher_id}


@router.delete("/classes/{class_id}", dependencies=[Depends(require_admin)])
def delete_empty_class(class_id: int, db: Session = Depends(get_db)) -> dict:
    class_ = _class(db, class_id)
    if db.query(Team.id).filter(Team.class_id == class_id).first() or db.query(Student.id).filter(
        Student.class_id == class_id
    ).first():
        raise HTTPException(status_code=409, detail="班级仍有小组或学生，不能删除")
    db.delete(class_)
    db.commit()
    return {"ok": True}


@router.get("/classes/{class_id}/teams", dependencies=[Depends(require_admin)])
def list_class_teams(class_id: int, db: Session = Depends(get_db)) -> list[dict]:
    _class(db, class_id)
    teams = db.query(Team).filter(Team.class_id == class_id).order_by(Team.id).all()
    return [{"id": team.id, "name": team.name} for team in teams]


@router.get("/students", dependencies=[Depends(require_admin)])
def list_students(
    class_id: int,
    query: str = "",
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
) -> dict:
    _class(db, class_id)
    students = db.query(Student).filter(Student.class_id == class_id)
    if query.strip():
        students = students.filter(or_(
            Student.name.contains(query.strip()),
            Student.student_no.contains(query.strip()),
            Student.phone.contains(query.strip()),
        ))
    total = students.count()
    items = students.options(selectinload(Student.team)).order_by(Student.id).offset(offset).limit(limit).all()
    return {"total": total, "items": [_student_response(student) for student in items]}


@router.post("/students", dependencies=[Depends(require_admin)])
def add_student(body: AdminStudentData, db: Session = Depends(get_db)) -> dict:
    _, team = _student_data(db, body)
    name = _required_text(body.name, "学生姓名", 64)
    student = Student(
        class_id=body.class_id,
        team_id=team.id if team else None,
        name=name,
        student_no=_optional_text(body.student_no, "学号", 32),
        phone=_optional_text(body.phone, "手机号", 20),
        grade=_optional_text(body.grade, "年级", 32),
        birth_date=body.birth_date,
        role=_optional_text(body.role, "职责", 64),
    )
    db.add(student)
    db.commit()
    db.refresh(student)
    return _student_response(student)


@router.put("/students/{student_id}", dependencies=[Depends(require_admin)])
def update_student(
    student_id: int, body: AdminStudentData, db: Session = Depends(get_db)
) -> dict:
    student = _student(db, student_id)
    if student.class_id != body.class_id:
        raise HTTPException(status_code=400, detail="不能通过此操作跨班转移学生")
    _, team = _student_data(db, body)
    student.name = _required_text(body.name, "学生姓名", 64)
    student.student_no = _optional_text(body.student_no, "学号", 32)
    student.phone = _optional_text(body.phone, "手机号", 20)
    student.grade = _optional_text(body.grade, "年级", 32)
    student.birth_date = body.birth_date
    student.role = _optional_text(body.role, "职责", 64)
    student.team_id = team.id if team else None
    db.commit()
    db.refresh(student)
    return _student_response(student)


@router.delete("/students/{student_id}", dependencies=[Depends(require_admin)])
def delete_unreferenced_student(student_id: int, db: Session = Depends(get_db)) -> dict:
    student = _student(db, student_id)
    has_work = db.query(MemberRecord.id).filter(MemberRecord.student_id == student_id).first()
    has_evaluation = db.query(Evaluation.id).filter(
        Evaluation.evaluator_role == "student", Evaluation.evaluator_id == student_id
    ).first() or db.query(Evaluation.id).filter(
        Evaluation.target_type.in_(("peer", "self")), Evaluation.target_id == student_id
    ).first()
    if has_work or has_evaluation:
        raise HTTPException(status_code=409, detail="学生已有实践或评价记录，不能删除")
    db.delete(student)
    db.commit()
    return {"ok": True}


@router.post("/students/{student_id}/login-code", dependencies=[Depends(require_admin)])
@router.post("/students/{student_id}/password", dependencies=[Depends(require_admin)])
def reset_student_login_code(student_id: int, db: Session = Depends(get_db)) -> dict:
    student = _student(db, student_id)
    try:
        code = reset_student_password(student)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from None
    db.commit()
    return {"code": code, "password": code}
