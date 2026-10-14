"""Access control and publication regression tests."""
from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path

_test_dir = tempfile.mkdtemp(prefix="aicourse-tests-")
os.environ["DATABASE_URL"] = f"sqlite:///{_test_dir}/test.db"
os.environ["JWT_SECRET_KEY"] = "test-only-secret"
os.environ["ADMIN_USERNAME"] = "admin"
os.environ["ADMIN_PASSWORD"] = "long-admin-password"

from fastapi.testclient import TestClient  # noqa: E402
from main import app  # noqa: E402
from database import SessionLocal  # noqa: E402
from models import Class_, Evaluation, MemberRecord, Practice, Student, Teacher, Team  # noqa: E402
from passwords import hash_password  # noqa: E402
from add_teacher import create_teacher  # noqa: E402
import main  # noqa: E402


class AccessTests(unittest.TestCase):
    def setUp(self) -> None:
        with SessionLocal() as db:
            for model in (Evaluation, MemberRecord, Practice, Student, Team, Class_, Teacher):
                db.query(model).delete()
            db.commit()
            first = Teacher(wechat_openid="first", name="First", password_hash=hash_password("password-for-first"))
            second = Teacher(wechat_openid="second", name="Second", password_hash=hash_password("password-for-second"))
            db.add_all((first, second))
            db.flush()
            first_class = Class_(teacher_id=first.id, name="First class")
            second_class = Class_(teacher_id=second.id, name="Second class")
            db.add_all((first_class, second_class))
            db.flush()
            team = Team(class_id=second_class.id, name="Second team")
            db.add(team)
            db.flush()
            practice = Practice(team_id=team.id, title="Private work")
            db.add(practice)
            student = Student(class_id=second_class.id, team_id=team.id, name="Student")
            db.add(student)
            db.flush()
            self.class_id = second_class.id
            self.team_id = team.id
            self.practice_id = practice.id
            self.student_id = student.id
            db.commit()
        self.client = TestClient(app)
        login = self.client.post("/api/auth/login", json={"name": "First", "password": "password-for-first"})
        self.assertEqual(login.status_code, 200)
        self.headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

    def admin_headers(self) -> dict[str, str]:
        login = self.client.post(
            "/api/admin/login", json={"username": "admin", "password": "long-admin-password"}
        )
        self.assertEqual(login.status_code, 200)
        return {"Authorization": f"Bearer {login.json()['access_token']}"}

    def test_rejects_wrong_password(self) -> None:
        response = self.client.post("/api/auth/login", json={"name": "Second", "password": "wrong"})
        self.assertEqual(response.status_code, 401)

    def test_create_teacher_and_reject_duplicate_name(self) -> None:
        with SessionLocal() as db:
            teacher = create_teacher(db, "New Teacher", "Example School", "long-new-password")
            self.assertEqual(teacher.school, "Example School")
            with self.assertRaises(ValueError):
                create_teacher(db, "New Teacher", "", "another-long-password")
        login = self.client.post(
            "/api/auth/login", json={"name": "New Teacher", "password": "long-new-password"}
        )
        self.assertEqual(login.status_code, 200)

    def test_admin_can_add_teacher_through_api(self) -> None:
        self.assertEqual(
            self.client.post(
                "/api/admin/teachers", json={"name": "Web Teacher", "password": "long-web-password"}
            ).status_code,
            403,
        )
        admin_login = self.client.post(
            "/api/admin/login", json={"username": "admin", "password": "long-admin-password"}
        )
        self.assertEqual(admin_login.status_code, 200)
        headers = {"Authorization": f"Bearer {admin_login.json()['access_token']}"}
        response = self.client.post(
            "/api/admin/teachers",
            headers=headers,
            json={"name": "Web Teacher", "school": "Example School", "password": "long-web-password"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["name"], "Web Teacher")
        self.assertEqual(
            self.client.post(
                "/api/admin/teachers", headers=headers,
                json={"name": "Web Teacher", "password": "another-long-password"},
            ).status_code,
            400,
        )

    def test_admin_dashboard_requires_admin_role(self) -> None:
        for path in ("/api/admin/overview", "/api/admin/teachers", "/api/admin/classes"):
            self.assertEqual(self.client.get(path, headers=self.headers).status_code, 403)
        self.assertEqual(
            self.client.put(
                f"/api/admin/teachers/{self.class_id}", headers=self.headers,
                json={"name": "Wrong", "authorized": False},
            ).status_code,
            403,
        )
        headers = self.admin_headers()
        overview = self.client.get("/api/admin/overview", headers=headers)
        self.assertEqual(overview.status_code, 200)
        self.assertEqual(overview.json()["teachers"], 2)
        self.assertEqual(overview.json()["students"], 1)

    def test_admin_edits_disables_and_resets_teacher(self) -> None:
        headers = self.admin_headers()
        teacher = next(item for item in self.client.get(
            "/api/admin/teachers", headers=headers
        ).json() if item["name"] == "Second")
        teacher_id = teacher["id"]
        owner = self.client.post(
            "/api/auth/login", json={"name": "Second", "password": "password-for-second"}
        )
        owner_headers = {"Authorization": f"Bearer {owner.json()['access_token']}"}
        edited = self.client.put(
            f"/api/admin/teachers/{teacher_id}", headers=headers,
            json={"name": "Renamed", "school": "New School", "authorized": False},
        )
        self.assertEqual(edited.status_code, 200)
        self.assertEqual(self.client.get("/api/classes", headers=owner_headers).status_code, 401)
        self.assertEqual(self.client.post(
            "/api/auth/login", json={"name": "Renamed", "password": "password-for-second"}
        ).status_code, 401)
        self.assertEqual(self.client.put(
            f"/api/admin/teachers/{teacher_id}", headers=headers,
            json={"name": "First", "school": "", "authorized": True},
        ).status_code, 400)
        self.assertEqual(self.client.put(
            f"/api/admin/teachers/{teacher_id}", headers=headers,
            json={"name": "Renamed", "school": "New School", "authorized": True},
        ).status_code, 200)
        self.assertEqual(self.client.post(
            f"/api/admin/teachers/{teacher_id}/password", headers=headers,
            json={"password": "short"},
        ).status_code, 400)
        self.assertEqual(self.client.post(
            f"/api/admin/teachers/{teacher_id}/password", headers=headers,
            json={"password": "replacement-password"},
        ).status_code, 200)
        self.assertEqual(self.client.get("/api/classes", headers=owner_headers).status_code, 401)
        self.assertEqual(self.client.post(
            "/api/auth/login", json={"name": "Renamed", "password": "password-for-second"}
        ).status_code, 401)
        self.assertEqual(self.client.post(
            "/api/auth/login", json={"name": "Renamed", "password": "replacement-password"}
        ).status_code, 200)

    def test_admin_password_reset_revokes_private_image_cookie(self) -> None:
        headers = self.admin_headers()
        owner = self.client.post(
            "/api/auth/login", json={"name": "Second", "password": "password-for-second"}
        )
        teacher_id = owner.json()["teacher_id"]
        with tempfile.TemporaryDirectory() as image_dir:
            original = main.PRACTICE_UPLOAD_DIR
            main.PRACTICE_UPLOAD_DIR = Path(image_dir)
            try:
                (Path(image_dir) / "before-reset.png").write_bytes(b"image")
                with SessionLocal() as db:
                    practice = db.get(Practice, self.practice_id)
                    practice.images = ["uploads/practices/before-reset.png"]
                    db.commit()
                url = "/uploads/practices/before-reset.png"
                self.assertEqual(self.client.get(url).status_code, 200)
                self.assertEqual(self.client.post(
                    f"/api/admin/teachers/{teacher_id}/password", headers=headers,
                    json={"password": "replacement-password"},
                ).status_code, 200)
                self.assertEqual(self.client.get(url).status_code, 404)
            finally:
                main.PRACTICE_UPLOAD_DIR = original

    def test_admin_manages_school_classes(self) -> None:
        headers = self.admin_headers()
        teacher_id = next(item["id"] for item in self.client.get(
            "/api/admin/teachers", headers=headers
        ).json() if item["name"] == "First")
        classes = self.client.get("/api/admin/classes", headers=headers)
        self.assertEqual(classes.status_code, 200)
        self.assertEqual(len(classes.json()), 2)
        self.assertEqual(self.client.delete(
            f"/api/admin/classes/{self.class_id}", headers=headers
        ).status_code, 409)
        transferred = self.client.put(
            f"/api/admin/classes/{self.class_id}", headers=headers,
            json={"teacher_id": teacher_id, "name": "Transferred", "grade": "2024", "description": "Moved"},
        )
        self.assertEqual(transferred.status_code, 200)
        self.assertEqual(self.client.get(
            f"/api/classes/{self.class_id}", headers=self.headers
        ).status_code, 200)
        created = self.client.post(
            "/api/admin/classes", headers=headers,
            json={"teacher_id": teacher_id, "name": "Empty class"},
        )
        self.assertEqual(created.status_code, 200)
        self.assertEqual(self.client.delete(
            f"/api/admin/classes/{created.json()['id']}", headers=headers
        ).status_code, 200)

    def test_admin_manages_students_with_safe_delete(self) -> None:
        headers = self.admin_headers()
        first_class_id = next(item["id"] for item in self.client.get(
            "/api/admin/classes", headers=headers
        ).json() if item["name"] == "First class")
        invalid = self.client.post(
            "/api/admin/students", headers=headers,
            json={"class_id": first_class_id, "team_id": self.team_id, "name": "New Student"},
        )
        self.assertEqual(invalid.status_code, 400)
        created = self.client.post(
            "/api/admin/students", headers=headers,
            json={"class_id": first_class_id, "name": "New Student", "student_no": "001"},
        )
        self.assertEqual(created.status_code, 200)
        student_id = created.json()["id"]
        listing = self.client.get(
            f"/api/admin/students?class_id={first_class_id}&query=001", headers=headers
        )
        self.assertEqual(listing.status_code, 200)
        self.assertEqual(listing.json()["total"], 1)
        updated = self.client.put(
            f"/api/admin/students/{student_id}", headers=headers,
            json={"class_id": first_class_id, "name": "Updated Student", "role": "记录"},
        )
        self.assertEqual(updated.status_code, 200)
        self.assertEqual(updated.json()["role"], "记录")
        code = self.client.post(
            f"/api/admin/students/{student_id}/login-code", headers=headers
        )
        self.assertEqual(code.status_code, 200)
        self.assertTrue(code.json()["code"])
        self.assertEqual(self.client.delete(
            f"/api/admin/students/{student_id}", headers=headers
        ).status_code, 200)
        with SessionLocal() as db:
            db.add(MemberRecord(
                practice_id=self.practice_id, student_id=self.student_id,
                work_description="Recorded observations",
            ))
            db.commit()
        self.assertEqual(self.client.delete(
            f"/api/admin/students/{self.student_id}", headers=headers
        ).status_code, 409)

    def test_rejects_foreign_resources(self) -> None:
        for path in (
            f"/api/classes/{self.class_id}",
            f"/api/teams/{self.team_id}",
            f"/api/practices/{self.practice_id}",
        ):
            self.assertEqual(self.client.get(path, headers=self.headers).status_code, 404)
        self.assertEqual(
            self.client.delete(f"/api/practices/{self.practice_id}", headers=self.headers).status_code,
            404,
        )

    def test_private_work_is_hidden_until_published(self) -> None:
        self.assertEqual(self.client.get("/api/practices/featured").json(), [])
        self.assertEqual(self.client.get(f"/api/practices/public/{self.practice_id}").status_code, 404)
        login = self.client.post("/api/auth/login", json={"name": "Second", "password": "password-for-second"})
        headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
        response = self.client.put(
            f"/api/practices/{self.practice_id}/publication?published=true", headers=headers
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(self.client.get("/api/practices/featured").json()), 1)
        self.assertEqual(self.client.get(f"/api/practices/public/{self.practice_id}").status_code, 200)

    def test_student_requires_teacher_issued_code(self) -> None:
        login_body = {"team_id": self.team_id, "name": "Student", "pin": "guessed"}
        self.assertEqual(self.client.post("/api/auth/student-login", json=login_body).status_code, 401)
        owner = self.client.post("/api/auth/login", json={"name": "Second", "password": "password-for-second"})
        owner_headers = {"Authorization": f"Bearer {owner.json()['access_token']}"}
        self.assertEqual(
            self.client.post(f"/api/students/{self.student_id}/login-code", headers=self.headers).status_code,
            404,
        )
        generated = self.client.post(
            f"/api/students/{self.student_id}/login-code", headers=owner_headers
        )
        self.assertEqual(generated.status_code, 200)
        login_body["pin"] = generated.json()["code"]
        self.assertEqual(self.client.post("/api/auth/student-login", json=login_body).status_code, 200)

    def test_rejects_non_image_upload(self) -> None:
        owner = self.client.post("/api/auth/login", json={"name": "Second", "password": "password-for-second"})
        headers = {"Authorization": f"Bearer {owner.json()['access_token']}"}
        response = self.client.post(
            f"/api/practices/team/{self.team_id}",
            headers=headers,
            data={"title": "Uploaded work"},
            files={"files": ("notes.txt", b"plain text", "text/plain")},
        )
        self.assertEqual(response.status_code, 400)

    def test_rejects_invalid_excel_without_importing(self) -> None:
        owner = self.client.post("/api/auth/login", json={"name": "Second", "password": "password-for-second"})
        headers = {"Authorization": f"Bearer {owner.json()['access_token']}"}
        response = self.client.post(
            f"/api/classes/{self.class_id}/import-excel",
            headers=headers,
            files={"file": ("students.xlsx", b"not an excel workbook")},
        )
        self.assertEqual(response.status_code, 400)

    def test_public_team_hides_members_without_published_work(self) -> None:
        response = self.client.get(f"/api/teams/public/{self.team_id}")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["members"], [])
        self.assertEqual(response.json()["practices"], [])

    def test_private_image_requires_owner_cookie(self) -> None:
        with tempfile.TemporaryDirectory() as image_dir:
            original = main.PRACTICE_UPLOAD_DIR
            main.PRACTICE_UPLOAD_DIR = Path(image_dir)
            try:
                (Path(image_dir) / "private.png").write_bytes(b"image")
                with SessionLocal() as db:
                    practice = db.get(Practice, self.practice_id)
                    practice.images = ["uploads/practices/private.png"]
                    db.commit()
                url = "/uploads/practices/private.png"
                self.assertEqual(self.client.get(url).status_code, 404)
                self.assertEqual(self.client.get(url, headers=self.headers).status_code, 404)
                owner = self.client.post(
                    "/api/auth/login", json={"name": "Second", "password": "password-for-second"}
                )
                self.assertEqual(owner.status_code, 200)
                self.assertEqual(self.client.get(url).status_code, 200)
            finally:
                main.PRACTICE_UPLOAD_DIR = original

    def test_private_image_rejects_disabled_teacher_cookie(self) -> None:
        with tempfile.TemporaryDirectory() as image_dir:
            original = main.PRACTICE_UPLOAD_DIR
            main.PRACTICE_UPLOAD_DIR = Path(image_dir)
            try:
                (Path(image_dir) / "disabled.png").write_bytes(b"image")
                with SessionLocal() as db:
                    practice = db.get(Practice, self.practice_id)
                    practice.images = ["uploads/practices/disabled.png"]
                    owner_id = practice.team.class_.teacher_id
                    db.commit()
                owner = self.client.post(
                    "/api/auth/login", json={"name": "Second", "password": "password-for-second"}
                )
                self.assertEqual(owner.status_code, 200)
                url = "/uploads/practices/disabled.png"
                self.assertEqual(self.client.get(url).status_code, 200)
                with SessionLocal() as db:
                    db.get(Teacher, owner_id).authorized = False
                    db.commit()
                self.assertEqual(self.client.get(url).status_code, 404)
            finally:
                main.PRACTICE_UPLOAD_DIR = original


if __name__ == "__main__":
    unittest.main()
