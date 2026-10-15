"""Small, versioned SQLite migrations for existing installations."""
from __future__ import annotations

from sqlalchemy import text

from database import Base, engine
import models  # noqa: F401 - register model metadata


def migrate() -> None:
    Base.metadata.create_all(bind=engine)
    migrations = {
        1: ("teachers", "school", "ALTER TABLE teachers ADD COLUMN school VARCHAR(128) NOT NULL DEFAULT ''"),
        2: ("teachers", "password_hash", "ALTER TABLE teachers ADD COLUMN password_hash VARCHAR(256)"),
        3: ("practices", "published", "ALTER TABLE practices ADD COLUMN published BOOLEAN NOT NULL DEFAULT 0"),
        4: ("students", "pin_hash", "ALTER TABLE students ADD COLUMN pin_hash VARCHAR(256)"),
        5: ("students", "phone", "ALTER TABLE students ADD COLUMN phone VARCHAR(20) NOT NULL DEFAULT ''"),
        6: ("practices", "submitted_by_student_id", "ALTER TABLE practices ADD COLUMN submitted_by_student_id INTEGER"),
        7: ("students", "must_change_password", "ALTER TABLE students ADD COLUMN must_change_password BOOLEAN NOT NULL DEFAULT 0"),
    }
    with engine.begin() as connection:
        version = connection.execute(text("PRAGMA user_version")).scalar_one()
        for number, (table, column, statement) in migrations.items():
            if number <= version:
                continue
            columns = {row[1] for row in connection.execute(text(f"PRAGMA table_info({table})"))}
            if column not in columns:
                connection.execute(text(statement))
            connection.execute(text(f"PRAGMA user_version = {number}"))


if __name__ == "__main__":
    migrate()
