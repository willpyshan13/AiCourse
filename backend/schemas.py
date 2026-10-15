from pydantic import BaseModel
from typing import Optional, List
from datetime import date, datetime


# ===== Teacher / Auth =====
class WeChatLoginRequest(BaseModel):
    name: str
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    teacher_id: int
    name: str
    school: str = ""

class TeacherInfo(BaseModel):
    id: int
    name: str
    school: str
    avatar_url: str
    created_at: datetime

    class Config:
        from_attributes = True


# ===== Class =====
class ClassCreate(BaseModel):
    name: str
    grade: str = ""
    description: str = ""

class ClassInfo(BaseModel):
    id: int
    teacher_id: int
    name: str
    grade: str
    description: str
    team_count: int = 0
    student_count: int = 0
    created_at: datetime

    class Config:
        from_attributes = True


# ===== Team =====
class TeamCreate(BaseModel):
    name: str

class TeamInfo(BaseModel):
    id: int
    class_id: int
    name: str
    qr_code: str
    member_count: int = 0
    practice_count: int = 0
    created_at: datetime

    class Config:
        from_attributes = True


# ===== Student =====
class StudentCreate(BaseModel):
    name: str
    student_no: str = ""
    phone: str = ""
    grade: str = ""
    birth_date: Optional[date] = None
    role: str = ""

class StudentUpdate(BaseModel):
    team_id: Optional[int] = None
    role: Optional[str] = None
    phone: Optional[str] = None

class StudentInfo(BaseModel):
    id: int
    class_id: int
    team_id: Optional[int]
    name: str
    student_no: str
    phone: str
    grade: str
    birth_date: Optional[date]
    role: str
    created_at: datetime

    class Config:
        from_attributes = True


# ===== Practice =====
class PracticeCreate(BaseModel):
    title: str
    content: str = ""

class MemberWorkRecord(BaseModel):
    student_id: int
    work_description: str

class PracticeWithMembers(BaseModel):
    id: int
    team_id: int
    title: str
    content: str
    images: List[str]
    ai_analysis: str
    ai_summary: str
    member_records: List[dict] = []
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ===== Evaluation =====
class EvaluationCreate(BaseModel):
    score: int  # 1-100
    comment: str = ""
    target_type: str = "practice"  # "peer" | "self" | "teacher" | "practice"
    target_id: Optional[int] = None  # student_id, teacher_id, or NULL for "practice"

class EvaluationDetail(BaseModel):
    id: int
    practice_id: int
    evaluator_role: str
    evaluator_id: int
    evaluator_name: str = ""
    target_type: str
    target_id: Optional[int] = None
    target_name: str = ""
    score: int
    comment: str
    created_at: datetime
    updated_at: datetime
    class Config:
        from_attributes = True


# ===== Student Auth =====
class StudentLoginRequest(BaseModel):
    team_id: int
    identifier: str
    password: str


class StudentPasswordChange(BaseModel):
    current_password: str
    new_password: str

class StudentTokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    student_id: int
    name: str
    team_id: int
    team_name: str = ""
    class_name: str = ""
    must_change_password: bool = False

    class Config:
        from_attributes = True


# ===== Excel Import =====
class ExcelImportResult(BaseModel):
    students_imported: int
    teams_created: int
    errors: List[str] = []


# ===== QR Code =====
class QRCodeData(BaseModel):
    team_id: int
    team_name: str
    class_name: str
    practices_url: str
    qr_base64: str
