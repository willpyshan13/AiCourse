"""Access control and publication regression tests."""
from __future__ import annotations

import io
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
from PIL import Image  # noqa: E402
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
            student = Student(
                class_id=second_class.id, team_id=team.id, name="Student",
                student_no="S001", phone="13800000001",
            )
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
            json={"class_id": first_class_id, "name": "New Student", "student_no": "001", "phone": "13800000002"},
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
            json={"class_id": first_class_id, "name": "Updated Student", "student_no": "001", "phone": "13800000002", "role": "记录"},
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

    def test_student_uses_phone_tail_as_initial_password(self) -> None:
        login_body = {"team_id": self.team_id, "identifier": "S001", "password": "guessed"}
        self.assertEqual(self.client.post("/api/auth/student-login", json=login_body).status_code, 401)
        login_body["password"] = "000001"
        first_login = self.client.post("/api/auth/student-login", json=login_body)
        self.assertEqual(first_login.status_code, 200)
        self.assertTrue(first_login.json()["must_change_password"])
        student_headers = {"Authorization": f"Bearer {first_login.json()['access_token']}"}
        self.assertEqual(self.client.get(
            f"/api/practices/student/team/{self.team_id}", headers=student_headers
        ).status_code, 403)
        self.assertEqual(self.client.post(
            f"/api/practices/{self.practice_id}/evaluations", headers=student_headers,
            json={"target_type": "self", "score": 80},
        ).status_code, 403)
        login_body["identifier"] = "13800000001"
        self.assertEqual(self.client.post("/api/auth/student-login", json=login_body).status_code, 200)
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
        self.assertEqual(generated.json()["password"], "000001")
        login_body["password"] = generated.json()["code"]
        self.assertEqual(self.client.post("/api/auth/student-login", json=login_body).status_code, 200)

    def test_student_password_reset_requires_valid_phone(self) -> None:
        with SessionLocal() as db:
            student = db.get(Student, self.student_id)
            student.phone = ""
            db.commit()
        owner = self.client.post(
            "/api/auth/login",
            json={"name": "Second", "password": "password-for-second"},
        )
        headers = {"Authorization": f"Bearer {owner.json()['access_token']}"}
        response = self.client.post(
            f"/api/students/{self.student_id}/password", headers=headers
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(self.client.post(
            "/api/auth/student-login",
            json={"team_id": self.team_id, "identifier": "S001", "password": "000001"},
        ).status_code, 401)

    def test_shared_phone_requires_student_number_in_same_team(self) -> None:
        with SessionLocal() as db:
            second_student = Student(
                class_id=self.class_id, team_id=self.team_id, name="Student",
                student_no="S002", phone="13800000001",
            )
            db.add(second_student)
            db.commit()
            second_student_id = second_student.id

        owner = self.client.post(
            "/api/auth/login",
            json={"name": "Second", "password": "password-for-second"},
        )
        owner_headers = {"Authorization": f"Bearer {owner.json()['access_token']}"}
        first_code = self.client.post(
            f"/api/students/{self.student_id}/login-code", headers=owner_headers
        ).json()["code"]
        second_code = self.client.post(
            f"/api/students/{second_student_id}/login-code", headers=owner_headers
        ).json()["code"]

        self.assertEqual(first_code, second_code)
        for identifier, code, expected_id in (
            ("S001", first_code, self.student_id),
            ("S002", second_code, second_student_id),
        ):
            response = self.client.post(
                "/api/auth/student-login",
                json={"team_id": self.team_id, "identifier": identifier, "password": code},
            )
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json()["student_id"], expected_id)

        shared_phone = self.client.post(
            "/api/auth/student-login",
            json={"team_id": self.team_id, "identifier": "13800000001", "password": first_code},
        )
        self.assertEqual(shared_phone.status_code, 409)

        invalid = self.client.post(
            "/api/auth/student-login",
            json={"team_id": self.team_id, "identifier": "S001", "password": "wrong"},
        )
        self.assertEqual(invalid.status_code, 401)

    def test_student_password_change_and_teacher_reset_revoke_login(self) -> None:
        owner = self.client.post(
            "/api/auth/login",
            json={"name": "Second", "password": "password-for-second"},
        )
        headers = {"Authorization": f"Bearer {owner.json()['access_token']}"}
        issued = self.client.post(
            f"/api/students/{self.student_id}/password", headers=headers
        ).json()["password"]
        login_body = {"team_id": self.team_id, "identifier": "S001", "password": issued}
        student_login = self.client.post("/api/auth/student-login", json=login_body)
        self.assertEqual(student_login.status_code, 200)
        student_headers = {"Authorization": f"Bearer {student_login.json()['access_token']}"}
        changed = self.client.post(
            "/api/auth/student-password", headers=student_headers,
            json={"current_password": issued, "new_password": "new-family-password"},
        )
        self.assertEqual(changed.status_code, 200)
        self.assertFalse(changed.json()["must_change_password"])
        self.assertEqual(self.client.get(
            f"/api/practices/student/team/{self.team_id}",
            headers={"Authorization": f"Bearer {changed.json()['access_token']}"},
        ).status_code, 200)
        self.assertEqual(self.client.get(
            f"/api/practices/student/team/{self.team_id}", headers=student_headers
        ).status_code, 401)
        self.assertEqual(self.client.post("/api/auth/student-login", json=login_body).status_code, 401)
        login_body["password"] = "new-family-password"
        new_login = self.client.post("/api/auth/student-login", json=login_body)
        self.assertEqual(new_login.status_code, 200)
        new_headers = {"Authorization": f"Bearer {new_login.json()['access_token']}"}
        self.client.post(f"/api/students/{self.student_id}/password", headers=headers)
        self.assertEqual(self.client.get(
            f"/api/practices/student/team/{self.team_id}", headers=new_headers
        ).status_code, 401)
        login_body["password"] = issued
        reset_login = self.client.post("/api/auth/student-login", json=login_body)
        self.assertEqual(reset_login.status_code, 200)
        self.assertTrue(reset_login.json()["must_change_password"])

    def test_family_can_upload_private_practice_for_own_team(self) -> None:
        owner = self.client.post(
            "/api/auth/login",
            json={"name": "Second", "password": "password-for-second"},
        )
        owner_headers = {"Authorization": f"Bearer {owner.json()['access_token']}"}
        password = self.client.post(
            f"/api/students/{self.student_id}/password", headers=owner_headers
        ).json()["password"]
        student_client = TestClient(app)
        login = student_client.post(
            "/api/auth/student-login",
            json={"team_id": self.team_id, "identifier": "13800000001", "password": password},
        )
        self.assertEqual(login.status_code, 200)
        self.assertTrue(login.json()["must_change_password"])
        initial_headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
        self.assertEqual(student_client.post(
            f"/api/practices/student/team/{self.team_id}",
            headers=initial_headers, data={"title": "Early", "content": "Blocked"},
        ).status_code, 403)
        changed = student_client.post(
            "/api/auth/student-password", headers=initial_headers,
            json={"current_password": password, "new_password": "family-upload-password"},
        )
        self.assertEqual(changed.status_code, 200)
        student_headers = {"Authorization": f"Bearer {changed.json()['access_token']}"}
        self.assertEqual(student_client.post(
            f"/api/practices/student/team/{self.team_id + 9999}",
            headers=student_headers, data={"title": "Other team", "content": "Blocked"},
        ).status_code, 404)
        image = Image.new("RGB", (2, 2), "blue")
        buffer = io.BytesIO()
        image.save(buffer, format="PNG")
        submitted = student_client.post(
            f"/api/practices/student/team/{self.team_id}", headers=student_headers,
            data={"title": "Family record", "content": "Observed three leaves"},
            files={"files": ("leaf.png", buffer.getvalue(), "image/png")},
        )
        self.assertEqual(submitted.status_code, 200)
        self.assertFalse(submitted.json()["published"])
        image_path = "/" + submitted.json()["images"][0]
        self.assertEqual(student_client.get(image_path).status_code, 200)
        self.assertEqual(TestClient(app).get(image_path).status_code, 404)
        own_records = student_client.get(
            f"/api/practices/student/team/{self.team_id}", headers=student_headers
        ).json()
        self.assertEqual(own_records[0]["title"], "Family record")
        public_records = self.client.get(f"/api/teams/public/{self.team_id}").json()["practices"]
        self.assertFalse(any(item["title"] == "Family record" for item in public_records))
        teacher_records = self.client.get(
            f"/api/practices/team/{self.team_id}", headers=owner_headers
        ).json()
        self.assertTrue(any(item["title"] == "Family record" for item in teacher_records))
        self.client.post(f"/api/students/{self.student_id}/password", headers=owner_headers)
        self.assertEqual(student_client.get(image_path).status_code, 404)
        reset_login = student_client.post(
            "/api/auth/student-login",
            json={"team_id": self.team_id, "identifier": "S001", "password": password},
        )
        self.assertTrue(reset_login.json()["must_change_password"])
        self.assertEqual(student_client.get(image_path).status_code, 404)

    def test_existing_phone_password_requires_change_after_upgrade(self) -> None:
        with SessionLocal() as db:
            student = db.get(Student, self.student_id)
            student.pin_hash = hash_password("000001")
            student.must_change_password = False
            db.commit()
        login = self.client.post(
            "/api/auth/student-login",
            json={"team_id": self.team_id, "identifier": "S001", "password": "000001"},
        )
        self.assertEqual(login.status_code, 200)
        self.assertTrue(login.json()["must_change_password"])

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
