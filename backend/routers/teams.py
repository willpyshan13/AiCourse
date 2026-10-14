from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session, selectinload
from typing import List
from database import get_db
from models import Team, Student, Practice, MemberRecord
from schemas import TeamInfo, StudentInfo
from auth import get_current_teacher
from ownership import owned_team
from utils.qrcode_gen import generate_team_qrcode

router = APIRouter(prefix="/api/teams", tags=["小组管理"])


@router.get("/{team_id}", response_model=TeamInfo)
def get_team(
    team_id: int,
    payload: dict = Depends(get_current_teacher),
    db: Session = Depends(get_db),
):
    team = owned_team(db, team_id, int(payload["sub"]))
    if not team:
        raise HTTPException(status_code=404, detail="小组不存在")
    return TeamInfo(
        id=team.id,
        class_id=team.class_id,
        name=team.name,
        qr_code=team.qr_code or "",
        member_count=len(team.members),
        practice_count=len(team.practices),
        created_at=team.created_at,
    )


@router.put("/{team_id}")
def update_team(
    team_id: int,
    name: str,
    payload: dict = Depends(get_current_teacher),
    db: Session = Depends(get_db),
):
    team = owned_team(db, team_id, int(payload["sub"]))
    if not team:
        raise HTTPException(status_code=404, detail="小组不存在")
    team.name = name
    db.commit()
    return {"ok": True}


@router.delete("/{team_id}")
def delete_team(
    team_id: int,
    payload: dict = Depends(get_current_teacher),
    db: Session = Depends(get_db),
):
    team = owned_team(db, team_id, int(payload["sub"]))
    if not team:
        raise HTTPException(status_code=404, detail="小组不存在")
    db.delete(team)
    db.commit()
    return {"ok": True}


@router.get("/{team_id}/members", response_model=List[StudentInfo])
def list_team_members(
    team_id: int,
    payload: dict = Depends(get_current_teacher),
    db: Session = Depends(get_db),
):
    owned_team(db, team_id, int(payload["sub"]))
    students = db.query(Student).filter(Student.team_id == team_id).all()
    return students


@router.get("/{team_id}/qrcode")
def get_team_qrcode(
    team_id: int,
    request: Request,
    payload: dict = Depends(get_current_teacher),
    db: Session = Depends(get_db),
):
    team = owned_team(db, team_id, int(payload["sub"]))
    if not team:
        raise HTTPException(status_code=404, detail="小组不存在")
    class_ = team.class_
    base_url = str(request.base_url).rstrip("/")
    url = f"{base_url}/team/{team_id}"
    qr_base64 = generate_team_qrcode(team_name=team.name, class_name=class_.name, url=url)
    qr_path = f"/uploads/qrcodes/team_{team_id}.png"
    team.qr_code = qr_path
    db.commit()
    return {"qr_base64": qr_base64, "qr_path": qr_path, "url": url}


@router.get("/public/{team_id}")
def get_team_public(team_id: int, db: Session = Depends(get_db)):
    """无需登录的公开接口 — 扫码后查看小组实践内容"""
    team = db.query(Team).filter(Team.id == team_id).first()
    if not team:
        raise HTTPException(status_code=404, detail="小组不存在")
    practices = db.query(Practice).filter(
        Practice.team_id == team_id, Practice.published.is_(True)
    ).options(selectinload(Practice.member_records).selectinload(MemberRecord.student)).order_by(Practice.created_at.desc()).all()
    members = db.query(Student).filter(Student.team_id == team_id).all() if practices else []
    return {
        "team": {
            "id": team.id,
            "name": team.name,
            "class_name": team.class_.name,
        },
        "members": [{"id": m.id, "name": m.name, "role": m.role} for m in members],
        "practices": [
            {
                "id": p.id,
                "title": p.title,
                "content": p.content,
                "images": p.images,
                "ai_analysis": p.ai_analysis,
                "ai_summary": p.ai_summary,
                "created_at": p.created_at.isoformat(),
                "member_records": [
                    {
                        "student_name": r.student.name if r.student else "",
                        "work_description": r.work_description,
                    }
                    for r in p.member_records
                ],
            }
            for p in practices
        ],
    }
