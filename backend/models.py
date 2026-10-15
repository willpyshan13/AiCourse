import datetime
import os
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Date, JSON
from sqlalchemy.orm import relationship
from sqlalchemy import Boolean
from database import Base


class Teacher(Base):
    __tablename__ = "teachers"

    id = Column(Integer, primary_key=True, index=True)
    wechat_openid = Column(String(128), unique=True, index=True, nullable=False)
    name = Column(String(64), nullable=False)
    school = Column(String(128), default="", nullable=False)
    avatar_url = Column(String(512), default="")
    authorized = Column(Boolean, default=True)  # 预留：严格模式下只有 authorized=True 才能登录
    password_hash = Column(String(256), nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    classes = relationship("Class_", back_populates="teacher")


class Class_(Base):
    __tablename__ = "classes"

    id = Column(Integer, primary_key=True, index=True)
    teacher_id = Column(Integer, ForeignKey("teachers.id"), nullable=False)
    name = Column(String(128), nullable=False)  # e.g. "2024级9班"
    grade = Column(String(32), default="")
    description = Column(Text, default="")
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    teacher = relationship("Teacher", back_populates="classes")
    teams = relationship("Team", back_populates="class_", cascade="all, delete-orphan")
    students = relationship("Student", back_populates="class_", cascade="all, delete-orphan")


class Team(Base):
    __tablename__ = "teams"

    id = Column(Integer, primary_key=True, index=True)
    class_id = Column(Integer, ForeignKey("classes.id"), nullable=False)
    name = Column(String(64), nullable=False)  # e.g. "第一组", "探索组"
    qr_code = Column(String(256), default="")
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    class_ = relationship("Class_", back_populates="teams")
    members = relationship("Student", back_populates="team")
    practices = relationship("Practice", back_populates="team", cascade="all, delete-orphan")


class Student(Base):
    __tablename__ = "students"

    id = Column(Integer, primary_key=True, index=True)
    class_id = Column(Integer, ForeignKey("classes.id"), nullable=False)
    team_id = Column(Integer, ForeignKey("teams.id"), nullable=True)
    name = Column(String(64), nullable=False)
    pin_hash = Column(String(256), nullable=True)
    must_change_password = Column(Boolean, default=False, nullable=False)
    student_no = Column(String(32), default="")
    phone = Column(String(20), default="", nullable=False)
    grade = Column(String(32), default="")
    birth_date = Column(Date, nullable=True)
    role = Column(String(64), default="")  # 职责: 动手实践/记录数据/分析数据/查阅资料等
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    class_ = relationship("Class_", back_populates="students")
    team = relationship("Team", back_populates="members")


class Practice(Base):
    __tablename__ = "practices"

    id = Column(Integer, primary_key=True, index=True)
    team_id = Column(Integer, ForeignKey("teams.id"), nullable=False)
    submitted_by_student_id = Column(Integer, ForeignKey("students.id"), nullable=True)
    title = Column(String(128), nullable=False)
    content = Column(Text, default="")
    images = Column(JSON, default=list)  # list of file paths
    ai_analysis = Column(Text, default="")
    ai_summary = Column(Text, default="")
    published = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    team = relationship("Team", back_populates="practices")
    evaluations = relationship("Evaluation", back_populates="practice", cascade="all, delete-orphan")
    member_records = relationship("MemberRecord", back_populates="practice", cascade="all, delete-orphan")


class MemberRecord(Base):
    """记录每次实践中每个成员的具体分工和贡献"""
    __tablename__ = "member_records"

    id = Column(Integer, primary_key=True, index=True)
    practice_id = Column(Integer, ForeignKey("practices.id"), nullable=False)
    student_id = Column(Integer, ForeignKey("students.id"), nullable=False)
    work_description = Column(Text, default="")
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    practice = relationship("Practice", back_populates="member_records")
    student = relationship("Student")
class Evaluation(Base):
    """评价：支持学生互评、自评、评老师、老师评实践"""
    __tablename__ = "evaluations"

    id = Column(Integer, primary_key=True, index=True)
    practice_id = Column(Integer, ForeignKey("practices.id"), nullable=False)
    evaluator_role = Column(String(16), nullable=False)  # "student" | "teacher"
    evaluator_id = Column(Integer, nullable=False)        # student_id or teacher_id
    target_type = Column(String(16), nullable=False)      # "peer" | "self" | "teacher" | "practice"
    target_id = Column(Integer, nullable=True)            # student_id, teacher_id, or NULL for "practice"
    score = Column(Integer, nullable=False)               # 百分制评分 1-100
    comment = Column(Text, default="")                    # 评语
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    practice = relationship("Practice", back_populates="evaluations")
