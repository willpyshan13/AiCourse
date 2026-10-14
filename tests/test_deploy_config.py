"""Deployment configuration must keep credentials stable across reinstallations."""
from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path

from dotenv import dotenv_values

from deploy.configure_env import create_config


class DeploymentConfigTests(unittest.TestCase):
    def test_creates_valid_config_and_preserves_existing_secret(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / ".env"
            password = 'long password # "quoted"'
            self.assertTrue(create_config(path, "school-admin", password))
            values = dotenv_values(path)
            self.assertEqual(values["ADMIN_USERNAME"], "school-admin")
            self.assertEqual(values["ADMIN_PASSWORD"], password)
            self.assertGreaterEqual(len(values["JWT_SECRET_KEY"]), 48)
            original = path.read_bytes()
            self.assertFalse(create_config(path, "other", "another-password"))
            self.assertEqual(path.read_bytes(), original)
            if os.name != "nt":
                self.assertEqual(path.stat().st_mode & 0o777, 0o600)

    def test_rejects_short_password_without_writing_config(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / ".env"
            with self.assertRaises(ValueError):
                create_config(path, "admin", "too-short")
            self.assertFalse(path.exists())

    def test_rejects_dotenv_variable_interpolation(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / ".env"
            with self.assertRaises(ValueError):
                create_config(path, "admin", "long${USER}password")
            self.assertFalse(path.exists())


if __name__ == "__main__":
    unittest.main()
