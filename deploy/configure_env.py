"""Create the local deployment configuration without exposing secrets in output."""
from __future__ import annotations

import argparse
import getpass
import json
import os
import secrets
from pathlib import Path


def create_config(path: Path, username: str, password: str) -> bool:
    """Write a new dotenv file; preserve an existing installation's credentials."""
    if path.exists():
        return False
    if not username or any(char in username for char in "\r\n") or "${" in username:
        raise ValueError("管理员用户名不能为空，且不能包含换行或 ${")
    if len(password) < 12 or any(char in password for char in "\r\n") or "${" in password:
        raise ValueError("管理员密码至少12位，且不能包含换行或 ${")

    settings = {
        "JWT_SECRET_KEY": secrets.token_urlsafe(48),
        "ADMIN_USERNAME": username,
        "ADMIN_PASSWORD": password,
    }
    contents = "".join(
        f"{key}={json.dumps(value, ensure_ascii=False)}\n"
        for key, value in settings.items()
    )
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8") as config:
        config.write(contents)
    return True


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("path", type=Path)
    args = parser.parse_args()
    if args.path.exists():
        print(f"保留现有配置：{args.path}")
        return
    username = input("管理员用户名 [admin]：").strip() or "admin"
    password = getpass.getpass("管理员密码（至少12位）：")
    if create_config(args.path, username, password):
        print(f"已创建配置：{args.path}")


if __name__ == "__main__":
    main()
