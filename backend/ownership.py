"""Queries scoped to the authenticated teacher."""
from __future__ import annotations

from fastapi import HTTPException
from sqlalchemy.orm import Session

from models import Class_, Practice, Student, Team


def owned_class(db: Session, class_id: int, teacher_id: int) -> Class_:
    item = db.query(Class_).filter_by(id=class_id, teacher_id=teacher_id).first()
    if item is None:
        raise HTTPException(status_code=404, detail="班级不存在")
    return item


def owned_team(db: Session, team_id: int, teacher_id: int) -> Team:
    item = db.query(Team).join(Class_).filter(
        Team.id == team_id, Class_.teacher_id == teacher_id
    ).first()
    if item is None:
        raise HTTPException(status_code=404, detail="小组不存在")
    return item


def owned_student(db: Session, student_id: int, teacher_id: int) -> Student:
    item = db.query(Student).join(Class_).filter(
        Student.id == student_id, Class_.teacher_id == teacher_id
    ).first()
    if item is None:
        raise HTTPException(status_code=404, detail="学生不存在")
    return item


def owned_practice(db: Session, practice_id: int, teacher_id: int) -> Practice:
    item = db.query(Practice).join(Team).join(Class_).filter(
        Practice.id == practice_id, Class_.teacher_id == teacher_id
    ).first()
    if item is None:
        raise HTTPException(status_code=404, detail="实践记录不存在")
    return item
