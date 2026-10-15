from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db
from models import Student
from schemas import StudentInfo, StudentUpdate
from auth import get_current_teacher
from ownership import owned_student, owned_team
from student_passwords import reset_student_password

router = APIRouter(prefix="/api/students", tags=["学生管理"])


@router.post("/{student_id}/login-code")
@router.post("/{student_id}/password")
def reset_student_login_code(
    student_id: int,
    payload: dict = Depends(get_current_teacher),
    db: Session = Depends(get_db),
):
    student = owned_student(db, student_id, int(payload["sub"]))
    try:
        code = reset_student_password(student)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from None
    db.commit()
    return {"code": code, "password": code}


@router.get("/{student_id}", response_model=StudentInfo)
def get_student(
    student_id: int,
    payload: dict = Depends(get_current_teacher),
    db: Session = Depends(get_db),
):
    student = owned_student(db, student_id, int(payload["sub"]))
    if not student:
        raise HTTPException(status_code=404, detail="学生不存在")
    return student


@router.put("/{student_id}", response_model=StudentInfo)
def update_student(
    student_id: int,
    req: StudentUpdate,
    payload: dict = Depends(get_current_teacher),
    db: Session = Depends(get_db),
):
    student = owned_student(db, student_id, int(payload["sub"]))
    if not student:
        raise HTTPException(status_code=404, detail="学生不存在")

    if req.team_id is not None:
        team = owned_team(db, req.team_id, int(payload["sub"]))
        if team.class_id != student.class_id:
            raise HTTPException(status_code=400, detail="小组不属于学生班级")
        student.team_id = req.team_id
    if req.role is not None:
        student.role = req.role
    if req.phone is not None:
        student.phone = req.phone.strip()

    db.commit()
    db.refresh(student)
    return student


@router.delete("/{student_id}")
def delete_student(
    student_id: int,
    payload: dict = Depends(get_current_teacher),
    db: Session = Depends(get_db),
):
    student = owned_student(db, student_id, int(payload["sub"]))
    if not student:
        raise HTTPException(status_code=404, detail="学生不存在")
    db.delete(student)
    db.commit()
    return {"ok": True}
