import os
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session

from config import ALLOWED_ORIGINS, JWT_SECRET_KEY, UPLOAD_DIR, PRACTICE_UPLOAD_DIR
from database import get_db
from auth import verify_token
from migrate import migrate
from models import Practice, Teacher
from routers import admin, auth, classes, students, teams, practices

if not JWT_SECRET_KEY:
    raise RuntimeError("JWT_SECRET_KEY must be configured before starting the service")
migrate()

app = FastAPI(title="智慧综合实践课堂 API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=bool(ALLOWED_ORIGINS),
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(admin.router)
app.include_router(classes.router)
app.include_router(students.router)
app.include_router(teams.router)
app.include_router(practices.router)

PRACTICE_UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
(UPLOAD_DIR / "qrcodes").mkdir(parents=True, exist_ok=True)

FRONTEND_DIR = os.path.join(os.path.dirname(__file__), "..", "frontend")


@app.get("/")
def serve_index():
    return FileResponse(os.path.join(FRONTEND_DIR, "index.html"))


@app.get("/team/{team_id}")
def serve_team_page(team_id: int):
    return FileResponse(os.path.join(FRONTEND_DIR, "index.html"))


@app.get("/css/{filename}")
def serve_css(filename: str):
    return FileResponse(os.path.join(FRONTEND_DIR, "css", filename))


@app.get("/js/{filename}")
def serve_js(filename: str):
    return FileResponse(os.path.join(FRONTEND_DIR, "js", filename))


@app.get("/api/health")
def health():
    return {"status": "ok", "service": "智慧综合实践课堂"}


@app.get("/uploads/practices/{filename}")
def serve_practice_image(filename: str, request: Request, db: Session = Depends(get_db)):
    if Path(filename).name != filename:
        raise HTTPException(status_code=404)
    image_path = PRACTICE_UPLOAD_DIR / filename
    if not image_path.is_file():
        raise HTTPException(status_code=404)
    relative_path = f"uploads/practices/{filename}"
    candidates = db.query(Practice).filter(Practice.images.contains(filename)).all()
    practices = [p for p in candidates if relative_path in (p.images or [])]
    if not practices:
        raise HTTPException(status_code=404)
    if not any(p.published for p in practices):
        token = request.cookies.get("teacher_media")
        if not token:
            raise HTTPException(status_code=404)
        try:
            payload = verify_token(token)
            if payload.get("role") != "teacher":
                raise ValueError
            teacher_id = int(payload["sub"])
        except (ValueError, KeyError, HTTPException):
            raise HTTPException(status_code=404) from None
        teacher = db.get(Teacher, teacher_id)
        if teacher is None or not teacher.authorized:
            raise HTTPException(status_code=404)
        if not any(p.team.class_.teacher_id == teacher_id for p in practices):
            raise HTTPException(status_code=404)
    return FileResponse(image_path)


app.mount("/uploads", StaticFiles(directory=str(UPLOAD_DIR)), name="uploads")
