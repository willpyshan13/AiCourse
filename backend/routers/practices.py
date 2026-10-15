from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session, selectinload
from typing import List, Optional
import aiofiles
from uuid import uuid4
from PIL import Image, UnidentifiedImageError
from config import PRACTICE_UPLOAD_DIR, MAX_IMAGE_BYTES
from database import get_db
from models import Practice, Team, MemberRecord, Student, Class_, Teacher, Evaluation
from schemas import EvaluationCreate
from auth import get_current_teacher, get_current_active_student
from ownership import owned_practice, owned_team
from utils.ai_analysis import analyze_practice

PRACTICE_UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

router = APIRouter(prefix="/api/practices", tags=["实践内容"])


def _enrich_evaluations(evaluations, db):
    """填充评价中的评价人/被评价人姓名"""
    student_ids = {
        identifier
        for e in evaluations
        for identifier in (
            e.evaluator_id if e.evaluator_role == "student" else None,
            e.target_id if e.target_type in ("peer", "self") else None,
        )
        if identifier is not None
    }
    teacher_ids = {
        identifier
        for e in evaluations
        for identifier in (
            e.evaluator_id if e.evaluator_role == "teacher" else None,
            e.target_id if e.target_type == "teacher" else None,
        )
        if identifier is not None
    }
    student_names = {
        student.id: student.name
        for student in db.query(Student).filter(Student.id.in_(student_ids)).all()
    } if student_ids else {}
    teacher_names = {
        teacher.id: teacher.name
        for teacher in db.query(Teacher).filter(Teacher.id.in_(teacher_ids)).all()
    } if teacher_ids else {}
    result = []
    for e in evaluations:
        evaluator_name = (student_names if e.evaluator_role == "student" else teacher_names).get(e.evaluator_id, "")
        target_name = (teacher_names if e.target_type == "teacher" else student_names).get(e.target_id, "")
        result.append({
            "id": e.id,
            "evaluator_role": e.evaluator_role,
            "evaluator_id": e.evaluator_id,
            "evaluator_name": evaluator_name,
            "target_type": e.target_type,
            "target_id": e.target_id,
            "target_name": target_name,
            "score": e.score,
            "comment": e.comment,
            "created_at": e.created_at.isoformat() if e.created_at else "",
        })
    return result


def _parse_member_records(raw: str, team_id: int, db: Session) -> list[dict]:
    import json

    try:
        records = json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        raise HTTPException(status_code=400, detail="成员记录格式无效") from None
    if not isinstance(records, list):
        raise HTTPException(status_code=400, detail="成员记录格式无效")
    allowed = {student.id for student in db.query(Student).filter(Student.team_id == team_id)}
    for record in records:
        if not isinstance(record, dict) or record.get("student_id") not in allowed:
            raise HTTPException(status_code=400, detail="成员不属于当前小组")
    return records


async def _save_practice_images(files: List[UploadFile]) -> list[str]:
    if len(files) > 9:
        raise HTTPException(status_code=400, detail="最多只能上传9张图片")
    verified_images = []
    for file in files:
        image_bytes = await file.read(MAX_IMAGE_BYTES + 1)
        if len(image_bytes) > MAX_IMAGE_BYTES:
            raise HTTPException(status_code=413, detail="单张图片不能超过10MB")
        try:
            import io
            with Image.open(io.BytesIO(image_bytes)) as image:
                image.verify()
                image_format = image.format
        except (UnidentifiedImageError, OSError):
            raise HTTPException(status_code=400, detail="图片格式无效") from None
        extension = {"JPEG": ".jpg", "PNG": ".png", "WEBP": ".webp"}.get(image_format)
        if extension is None:
            raise HTTPException(status_code=400, detail="仅支持 JPEG、PNG、WebP 图片")
        verified_images.append((f"{uuid4().hex}{extension}", image_bytes))
    saved_images = []
    for filename, image_bytes in verified_images:
        async with aiofiles.open(PRACTICE_UPLOAD_DIR / filename, "wb") as output:
            await output.write(image_bytes)
        saved_images.append(f"uploads/practices/{filename}")
    return saved_images


@router.get("/team/{team_id}", response_model=List[dict])
def list_practices(
    team_id: int,
    payload: dict = Depends(get_current_teacher),
    db: Session = Depends(get_db),
):
    owned_team(db, team_id, int(payload["sub"]))
    practices = db.query(Practice).options(selectinload(Practice.evaluations), selectinload(Practice.member_records)).filter(Practice.team_id == team_id).order_by(Practice.created_at.desc()).all()
    result = []
    for p in practices:
        # 统计老师评价的平均分
        all_evals = p.evaluations
        teacher_eval = next((e for e in all_evals if e.evaluator_role == "teacher"), None)
        peer_evals = [e for e in all_evals if e.target_type == "peer"]
        avg_score = round(sum(e.score for e in peer_evals) / len(peer_evals)) if peer_evals else None

        result.append({
            "id": p.id,
            "title": p.title,
            "content": p.content,
            "images": p.images,
            "ai_analysis": p.ai_analysis,
            "ai_summary": p.ai_summary,
            "published": p.published,
            "submitted_by_student_id": p.submitted_by_student_id,
            "teacher_score": teacher_eval.score if teacher_eval else None,
            "peer_avg_score": avg_score,
            "member_count": len(p.member_records),
            "created_at": p.created_at.isoformat(),
        })
    return result


@router.get("/featured")
def get_featured_practices(db: Session = Depends(get_db)):
    """公开接口 - 获取优秀实践作品列表（无需登录）"""
    practices = (
        db.query(Practice)
        .join(Team)
        .join(Class_)
        .filter(Practice.published.is_(True))
        .options(selectinload(Practice.member_records), selectinload(Practice.team).selectinload(Team.class_))
        .order_by(Practice.created_at.desc())
        .limit(20)
        .all()
    )
    result = []
    for p in practices:
        class_name = p.team.class_.name if p.team and p.team.class_ else ""
        result.append({
            "id": p.id,
            "title": p.title,
            "content": p.content[:300] if p.content else "",
            "images": p.images or [],
            "ai_analysis": p.ai_analysis or "",
            "ai_summary": p.ai_summary or "",
            "team_name": p.team.name if p.team else "",
            "class_name": class_name,
            "member_count": len(p.member_records),
            "created_at": p.created_at.isoformat() if p.created_at else "",
        })
    return result


@router.put("/{practice_id}/publication")
def set_publication(
    practice_id: int,
    published: bool,
    payload: dict = Depends(get_current_teacher),
    db: Session = Depends(get_db),
):
    practice = owned_practice(db, practice_id, int(payload["sub"]))
    practice.published = published
    db.commit()
    return {"published": practice.published}


@router.post("/team/{team_id}", response_model=dict)
async def create_practice(
    team_id: int,
    title: str = Form(...),
    content: str = Form(""),
    member_works: Optional[str] = Form("[]"),
    files: List[UploadFile] = File(default=[]),
    payload: dict = Depends(get_current_teacher),
    db: Session = Depends(get_db),
):
    team = owned_team(db, team_id, int(payload["sub"]))
    if not team:
        raise HTTPException(status_code=404, detail="小组不存在")
    member_records_data = _parse_member_records(member_works, team_id, db)
    saved_images = await _save_practice_images(files)

    practice = Practice(team_id=team_id, title=title, content=content, images=saved_images)
    db.add(practice)
    db.flush()
    for rec in member_records_data:
        db.add(MemberRecord(
            practice_id=practice.id,
            student_id=rec.get("student_id"),
            work_description=rec.get("work_description", ""),
        ))

    members = db.query(Student).filter(Student.team_id == team_id).all()
    member_text = "\n".join([
        f"- {m.name}（{m.role or '未分配职责'}）：{next((r.get('work_description', '') for r in member_records_data if r.get('student_id') == m.id), '未记录')}"
        for m in members
    ])
    try:
        analysis = await analyze_practice(title, content, member_text)
        practice.ai_analysis = analysis.get("analysis", "")
        practice.ai_summary = analysis.get("summary", "")
    except Exception:
        practice.ai_analysis = "参考分析暂不可用"
        practice.ai_summary = ""

    db.commit()
    db.refresh(practice)
    return {
        "id": practice.id, "title": practice.title, "content": practice.content,
        "images": practice.images, "ai_analysis": practice.ai_analysis,
        "ai_summary": practice.ai_summary, "member_records": member_records_data,
        "created_at": practice.created_at.isoformat(),
    }


@router.get("/student/team/{team_id}")
def list_student_submissions(
    team_id: int,
    student: dict = Depends(get_current_active_student),
    db: Session = Depends(get_db),
) -> list[dict]:
    if student["team_id"] != team_id:
        raise HTTPException(status_code=404, detail="小组不存在")
    practices = db.query(Practice).filter(
        Practice.team_id == team_id,
        Practice.submitted_by_student_id == student["student_id"],
    ).order_by(Practice.created_at.desc()).all()
    return [{
        "id": practice.id,
        "title": practice.title,
        "content": practice.content,
        "images": practice.images or [],
        "published": practice.published,
        "submitted_by_student_id": practice.submitted_by_student_id,
        "created_at": practice.created_at.isoformat(),
    } for practice in practices]


@router.post("/student/team/{team_id}")
async def create_student_submission(
    team_id: int,
    title: str = Form(...),
    content: str = Form(""),
    files: List[UploadFile] = File(default=[]),
    student: dict = Depends(get_current_active_student),
    db: Session = Depends(get_db),
) -> dict:
    if student["team_id"] != team_id:
        raise HTTPException(status_code=404, detail="小组不存在")
    title = title.strip()
    content = content.strip()
    if not title or len(title) > 128 or len(content) > 10000:
        raise HTTPException(status_code=400, detail="标题或内容长度无效")
    if not content and not files:
        raise HTTPException(status_code=400, detail="请填写记录或上传图片")
    images = await _save_practice_images(files)
    practice = Practice(
        team_id=team_id, title=title, content=content, images=images,
        submitted_by_student_id=student["student_id"], published=False,
    )
    db.add(practice)
    db.flush()
    db.add(MemberRecord(
        practice_id=practice.id,
        student_id=student["student_id"],
        work_description="家庭提交",
    ))
    try:
        analysis = await analyze_practice(title, content, f"- {student['name']}：家庭提交")
        practice.ai_analysis = analysis.get("analysis", "")
        practice.ai_summary = analysis.get("summary", "")
    except Exception:
        practice.ai_analysis = "参考分析暂不可用"
        practice.ai_summary = ""
    db.commit()
    db.refresh(practice)
    return {"id": practice.id, "title": practice.title, "images": images, "published": False}


@router.get("/{practice_id}", response_model=dict)
def get_practice(
    practice_id: int,
    payload: dict = Depends(get_current_teacher),
    db: Session = Depends(get_db),
):
    practice = owned_practice(db, practice_id, int(payload["sub"]))
    if not practice:
        raise HTTPException(status_code=404, detail="实践记录不存在")
    all_evals = db.query(Evaluation).filter(Evaluation.practice_id == practice_id).all()
    return {
        "id": practice.id,
        "team_id": practice.team_id,
        "title": practice.title,
        "content": practice.content,
        "images": practice.images,
        "ai_analysis": practice.ai_analysis,
        "ai_summary": practice.ai_summary,
        "published": practice.published,
        "evaluations": _enrich_evaluations(all_evals, db),
        "member_records": [
            {
                "student_id": r.student_id,
                "student_name": r.student.name if r.student else "",
                "work_description": r.work_description,
            }
            for r in practice.member_records
        ],
        "created_at": practice.created_at.isoformat(),
        "updated_at": practice.updated_at.isoformat(),
    }


@router.put("/{practice_id}")
def update_practice(
    practice_id: int,
    title: str = Form(...),
    content: str = Form(""),
    member_works: str = Form("[]"),
    files: List[UploadFile] = File(default=[]),
    payload: dict = Depends(get_current_teacher),
    db: Session = Depends(get_db),
):
    practice = owned_practice(db, practice_id, int(payload["sub"]))
    if not practice:
        raise HTTPException(status_code=404, detail="实践记录不存在")
    practice.title = title
    practice.content = content
    records_data = _parse_member_records(member_works, practice.team_id, db)
    for r in practice.member_records:
        db.delete(r)
    for rec in records_data:
        db.add(MemberRecord(
            practice_id=practice.id,
            student_id=rec.get("student_id"),
            work_description=rec.get("work_description", ""),
        ))
    db.commit()
    return {"ok": True}


@router.delete("/{practice_id}")
def delete_practice(
    practice_id: int,
    payload: dict = Depends(get_current_teacher),
    db: Session = Depends(get_db),
):
    practice = owned_practice(db, practice_id, int(payload["sub"]))
    if not practice:
        raise HTTPException(status_code=404, detail="实践记录不存在")
    db.delete(practice)
    db.commit()
    return {"ok": True}


@router.post("/{practice_id}/ai-reanalyze", response_model=dict)
async def reanalyze_practice(
    practice_id: int,
    payload: dict = Depends(get_current_teacher),
    db: Session = Depends(get_db),
):
    practice = owned_practice(db, practice_id, int(payload["sub"]))
    if not practice:
        raise HTTPException(status_code=404, detail="实践记录不存在")
    members = db.query(Student).filter(Student.team_id == practice.team_id).all()
    member_text = "\n".join([f"- {m.name}（{m.role or '未分配职责'}）" for m in members])
    try:
        analysis = await analyze_practice(practice.title, practice.content, member_text)
        practice.ai_analysis = analysis.get("analysis", "")
        practice.ai_summary = analysis.get("summary", "")
        db.commit()
        return {"ai_analysis": practice.ai_analysis, "ai_summary": practice.ai_summary}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"参考分析失败: {str(e)}")


@router.get("/public/{practice_id}")
def get_practice_public(practice_id: int, db: Session = Depends(get_db)):
    """公开接口 - 获取实践详情（无需登录）"""
    practice = db.query(Practice).filter(Practice.id == practice_id, Practice.published.is_(True)).first()
    if not practice:
        raise HTTPException(status_code=404, detail="实践记录不存在")
    team = db.query(Team).filter(Team.id == practice.team_id).first()
    class_name = team.class_.name if team and team.class_ else ""
    all_evals = db.query(Evaluation).filter(Evaluation.practice_id == practice_id).all()
    return {
        "id": practice.id,
        "title": practice.title,
        "content": practice.content,
        "images": practice.images or [],
        "ai_analysis": practice.ai_analysis or "",
        "ai_summary": practice.ai_summary or "",
        "evaluations": _enrich_evaluations(all_evals, db),
        "team_name": team.name if team else "",
        "class_name": class_name,
        "member_records": [
            {"student_name": r.student.name if r.student else "", "work_description": r.work_description}
            for r in practice.member_records
        ],
        "created_at": practice.created_at.isoformat() if practice.created_at else "",
    }


# ── 教师评价实践 ──
@router.post("/{practice_id}/evaluate")
def evaluate_practice(
    practice_id: int,
    body: EvaluationCreate,
    payload: dict = Depends(get_current_teacher),
    db: Session = Depends(get_db),
):
    practice = owned_practice(db, practice_id, int(payload["sub"]))
    if not practice:
        raise HTTPException(status_code=404, detail="实践记录不存在")
    if body.score < 1 or body.score > 100:
        raise HTTPException(status_code=400, detail="评分需在 1-100 之间")

    teacher_id = int(payload["sub"])
    # 查找或创建老师的评价
    evaluation = db.query(Evaluation).filter(
        Evaluation.practice_id == practice_id,
        Evaluation.evaluator_role == "teacher",
        Evaluation.evaluator_id == teacher_id,
    ).first()
    if evaluation:
        evaluation.score = body.score
        evaluation.comment = body.comment
    else:
        evaluation = Evaluation(
            practice_id=practice_id,
            evaluator_role="teacher",
            evaluator_id=teacher_id,
            target_type="practice",
            target_id=None,
            score=body.score,
            comment=body.comment,
        )
        db.add(evaluation)
    db.commit()
    db.refresh(evaluation)
    return _enrich_evaluations([evaluation], db)[0]


# ── 学生评价（互评/自评/评老师） ──
@router.post("/{practice_id}/evaluations")
def create_student_evaluation(
    practice_id: int,
    body: EvaluationCreate,
    student: dict = Depends(get_current_active_student),
    db: Session = Depends(get_db),
):
    practice = db.query(Practice).filter(Practice.id == practice_id, Practice.published.is_(True)).first()
    if not practice:
        raise HTTPException(status_code=404, detail="实践记录不存在")
    if practice.team_id != student["team_id"]:
        raise HTTPException(status_code=404, detail="实践记录不存在")
    if body.score < 1 or body.score > 100:
        raise HTTPException(status_code=400, detail="评分需在 1-100 之间")

    # 校验 target_type 合法性
    if body.target_type not in ("peer", "self", "teacher"):
        raise HTTPException(status_code=400, detail="评价类型无效: peer/self/teacher")

    # 校验 target_id
    if body.target_type == "self":
        target_id = student["student_id"]
    elif body.target_type == "peer":
        if not body.target_id:
            raise HTTPException(status_code=400, detail="请指定被评同学ID")
        # 检查是否是同组同学
        target = db.query(Student).filter(
            Student.id == body.target_id,
            Student.team_id == student["team_id"],
        ).first()
        if not target:
            raise HTTPException(status_code=400, detail="被评同学不在本组")
        target_id = body.target_id
    elif body.target_type == "teacher":
        # 找到该小组班级的老师
        team = db.query(Team).filter(Team.id == student["team_id"]).first()
        if not team:
            raise HTTPException(status_code=404, detail="小组不存在")
        target_id = team.class_.teacher_id
        if not target_id:
            raise HTTPException(status_code=400, detail="未找到班级老师")
    else:
        raise HTTPException(status_code=400, detail="无效的评价类型")

    # 检查是否已评过（每人每种类型只能评一次）
    existing = db.query(Evaluation).filter(
        Evaluation.practice_id == practice_id,
        Evaluation.evaluator_role == "student",
        Evaluation.evaluator_id == student["student_id"],
        Evaluation.target_type == body.target_type,
        Evaluation.target_id == target_id,
    ).first()
    if existing:
        existing.score = body.score
        existing.comment = body.comment
        db.commit()
        db.refresh(existing)
        return _enrich_evaluations([existing], db)[0]

    evaluation = Evaluation(
        practice_id=practice_id,
        evaluator_role="student",
        evaluator_id=student["student_id"],
        target_type=body.target_type,
        target_id=target_id,
        score=body.score,
        comment=body.comment,
    )
    db.add(evaluation)
    db.commit()
    db.refresh(evaluation)
    return _enrich_evaluations([evaluation], db)[0]


# ── 获取某次实践的全部评价 ──
@router.get("/{practice_id}/evaluations")
def list_evaluations(
    practice_id: int,
    role: Optional[str] = None,  # "teacher" or "student"
    db: Session = Depends(get_db),
):
    """获取某次实践的全部评价（无需登录，公开 API）"""
    practice = db.query(Practice).filter(Practice.id == practice_id, Practice.published.is_(True)).first()
    if not practice:
        raise HTTPException(status_code=404, detail="实践记录不存在")
    query = db.query(Evaluation).filter(Evaluation.practice_id == practice_id)
    if role:
        query = query.filter(Evaluation.evaluator_role == role)
    all_evals = query.all()
    return _enrich_evaluations(all_evals, db)
