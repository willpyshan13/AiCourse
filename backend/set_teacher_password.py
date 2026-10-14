"""Set a password for one existing teacher without changing their data."""
from __future__ import annotations

import argparse
import getpass

from passwords import hash_password
from database import SessionLocal
from migrate import migrate
from models import Teacher


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("teacher_id", type=int)
    args = parser.parse_args()
    migrate()
    password = getpass.getpass("New teacher password: ")
    if len(password) < 12:
        parser.error("Password must contain at least 12 characters")
    with SessionLocal() as db:
        teacher = db.get(Teacher, args.teacher_id)
        if teacher is None:
            parser.error("Teacher not found")
        teacher.password_hash = hash_password(password)
        db.commit()
    print("Password updated")


if __name__ == "__main__":
    main()
