"""Provision an existing student's private login code."""
from __future__ import annotations

import argparse
import getpass

from database import SessionLocal
from migrate import migrate
from models import Student
from passwords import hash_password


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("student_id", type=int)
    args = parser.parse_args()
    migrate()
    pin = getpass.getpass("New student code (at least 8 characters): ")
    if len(pin) < 8:
        parser.error("Student code must contain at least 8 characters")
    with SessionLocal() as db:
        student = db.get(Student, args.student_id)
        if student is None:
            parser.error("Student not found")
        student.pin_hash = hash_password(pin)
        db.commit()
    print("Student code updated")


if __name__ == "__main__":
    main()
