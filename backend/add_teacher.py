"""Create a teacher account from the administrator's terminal."""
from __future__ import annotations

import argparse
import getpass
from uuid import uuid4

from sqlalchemy.orm import Session

from database import SessionLocal
from migrate import migrate
from models import Teacher
from passwords import hash_password


def create_teacher(db: Session, name: str, school: str, password: str) -> Teacher:
    name = name.strip()
    school = school.strip()
    if not name:
        raise ValueError("Teacher name cannot be empty")
    if len(name) > 64 or len(school) > 128:
        raise ValueError("Name or school is too long")
    if len(password) < 12:
        raise ValueError("Password must contain at least 12 characters")
    if db.query(Teacher).filter(Teacher.name == name).first():
        raise ValueError("A teacher with this name already exists")
    teacher = Teacher(
        wechat_openid=f"admin_{uuid4().hex}",
        name=name,
        school=school,
        password_hash=hash_password(password),
        authorized=True,
    )
    db.add(teacher)
    db.commit()
    db.refresh(teacher)
    return teacher


def main() -> None:
    parser = argparse.ArgumentParser(description="Create a teacher account")
    parser.add_argument("name", help="Unique teacher login name")
    parser.add_argument("--school", default="", help="School name")
    args = parser.parse_args()
    password = getpass.getpass("New teacher password (at least 12 characters): ")
    confirmation = getpass.getpass("Confirm password: ")
    if password != confirmation:
        parser.error("Passwords do not match")
    migrate()
    try:
        with SessionLocal() as db:
            teacher = create_teacher(db, args.name, args.school, password)
    except ValueError as exc:
        parser.error(str(exc))
    print(f"Teacher created: ID={teacher.id}, name={teacher.name}")


if __name__ == "__main__":
    main()
