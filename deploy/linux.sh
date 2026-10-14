#!/usr/bin/env bash
# Install and run AiCourse as a systemd service on Ubuntu/Debian.
set -euo pipefail

if [[ "$(uname -s)" != "Linux" ]] || ! command -v apt-get >/dev/null; then
    echo "此脚本仅支持使用 apt 的 Ubuntu/Debian Linux。" >&2
    exit 1
fi
if [[ "$EUID" -eq 0 ]]; then
    echo "请以有 sudo 权限的普通用户运行：bash deploy/linux.sh" >&2
    exit 1
fi
if ! command -v sudo >/dev/null || ! command -v systemctl >/dev/null; then
    echo "需要 sudo 和 systemd。" >&2
    exit 1
fi

project_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
if [[ "$project_dir" == *[[:space:]]* ]]; then
    echo "项目路径不能包含空格，请移至如 /opt/aicourse 后重试。" >&2
    exit 1
fi
cd "$project_dir"

sudo apt-get update
sudo apt-get install -y python3 python3-venv python3-pip curl
python3 -m venv venv
venv/bin/python -m pip install -r backend/requirements.txt
venv/bin/python deploy/configure_env.py "$project_dir/.env"
mkdir -p data uploads/practices uploads/qrcodes

service_user="$(id -un)"
sudo tee /etc/systemd/system/aicourse.service >/dev/null <<UNIT
[Unit]
Description=AiCourse classroom service
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=$service_user
WorkingDirectory=$project_dir
ExecStart=$project_dir/venv/bin/python -m uvicorn main:app --app-dir backend --env-file $project_dir/.env --host 0.0.0.0 --port 8000
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
UNIT
sudo systemctl daemon-reload
sudo systemctl enable aicourse
sudo systemctl restart aicourse

healthy=false
for attempt in {1..10}; do
    if curl --fail --silent --max-time 2 http://127.0.0.1:8000/api/health >/dev/null; then
        healthy=true
        break
    fi
    sleep 1
done
if [[ "$healthy" != true ]]; then
    echo "服务未通过健康检查，请查看：sudo journalctl -u aicourse -n 100" >&2
    exit 1
fi
printf '\n部署完成。局域网地址：http://<这台电脑的IP>:8000\n'
echo "查看状态：sudo systemctl status aicourse"
echo "如果其他设备无法访问，请检查系统防火墙和校园网的设备互访规则。"
