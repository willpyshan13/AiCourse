"""Initial and reset passwords for student and family accounts."""
from __future__ import annotations

import hmac
import re

from models import Student
from passwords import hash_password, verify_password


PHONE_PATTERN = re.compile(r"1[3-9]\d{9}\Z")


def default_student_password(phone: str | None) -> str | None:
    value = (phone or "").strip()
    if not PHONE_PATTERN.fullmatch(value):
        return None
    return value[-6:]


def verify_student_password(student: Student, password: str) -> bool:
    if student.pin_hash:
        return verify_password(password, student.pin_hash)
    initial = default_student_password(student.phone)
    return initial is not None and hmac.compare_digest(password, initial)


def reset_student_password(student: Student) -> str:
    password = default_student_password(student.phone)
    if password is None:
        raise ValueError("请先填写有效的11位手机号")
    student.pin_hash = hash_password(password)
    student.must_change_password = True
    return password
