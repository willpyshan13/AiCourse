# 智慧综合实践课堂

FastAPI 后端和原生 JavaScript 前端。默认使用 `data/practice_classroom.db`。

## 启动

```sh
python3 -m venv venv
venv/bin/pip install -r backend/requirements.txt
export JWT_SECRET_KEY="请设置一个足够长的随机密钥"
export ADMIN_USERNAME="admin"
export ADMIN_PASSWORD="请设置至少12位的管理员密码"
PYTHONPATH=backend venv/bin/uvicorn main:app --app-dir backend
```

生产环境必须设置 `JWT_SECRET_KEY`。同源前端无需配置 CORS；若跨域部署，设置逗号分隔的 `ALLOWED_ORIGINS`。可用 `DATABASE_URL` 指向其他 SQLite 数据库。上传目录固定在项目根目录 `uploads/`。

启动时运行版本化的 SQLite 迁移，新增字段只追加，不会自动公开旧作品。部署前请备份 `data/practice_classroom.db` 和 `uploads/`。

## 账号

配置 `ADMIN_USERNAME` 和 `ADMIN_PASSWORD` 后，在网页教师登录页点击“管理员添加教师”，登录后填写教师信息即可新增。管理员密码至少 12 位；这两个环境变量只需在服务器启动时配置，网页不会显示它们。

命令行脚本仍可作为备用方式：

```sh
PYTHONPATH=backend venv/bin/python backend/add_teacher.py "张老师" --school "示例小学"
```

教师随后在网页的“教师登录”页面输入相同姓名和密码。姓名必须唯一，密码至少 12 位。学校参数可省略。

已有教师首次设置密码或重置密码：

```sh
PYTHONPATH=backend venv/bin/python -c 'from database import SessionLocal; from models import Teacher; db=SessionLocal(); print([(t.id,t.name) for t in db.query(Teacher).all()]); db.close()'
PYTHONPATH=backend venv/bin/python backend/set_teacher_password.py <教师ID>
```

密码会在终端隐式输入。历史数据若已有同名教师，这些账号暂时无法通过姓名登录，需要先整理为唯一姓名。

学生由所属教师在学生详情中生成个人登录口令，然后私下发给学生。重新生成会使旧口令无法再次登录。现有学生需要逐人生成口令，原先仅输入姓名的登录方式已停用。

教师在小组的实践列表中点击“公开作品”后，作品才会出现在首页和小组公开页。旧作品默认不公开。
未公开作品的图片需教师登录后由同源浏览器访问；退出登录会清除图片访问 Cookie。

## 测试

```sh
PYTHONPATH=backend venv/bin/python -m unittest discover -s tests -v
node --check frontend/js/app.js
node --check frontend/js/api.js
```

## 参考分析

提交实践记录时，系统根据填写的活动内容和成员分工生成参考分析与摘要；教师可在详情页重新生成。分析采用本地规则，不调用外部 AI 服务，也不据字数推断实践成果。请结合原始记录核对建议。

## 校园局域网部署

### 一键部署

从仓库克隆到 Windows 本机磁盘后，安装 Python 3，在**管理员 PowerShell** 中执行：

```powershell
cd C:\AiCourse
powershell -NoProfile -ExecutionPolicy Bypass -File .\deploy\windows.ps1
```

脚本会安装依赖、首次询问管理员密码、生成并保存密钥、创建开机启动任务，并开放仅限本地子网访问的 8000 端口。重复运行会保留现有 `.env`、数据库和上传文件。部署电脑保持开机后，其他设备访问 `http://<部署电脑IPv4地址>:8000`。如果学校把设备分在不同子网，请联系网管调整互访及防火墙规则。

Ubuntu/Debian Linux 在项目目录中执行：

```sh
bash deploy/linux.sh
```

请使用有 `sudo` 权限的普通用户。脚本安装依赖、保存 `.env`，并创建 `aicourse` systemd 服务。通过 `sudo systemctl status aicourse` 查看状态；如果系统防火墙已启用，还需由管理员允许校园局域网访问 TCP 8000 端口。Linux 脚本需要项目路径不含空格。

### Windows 手动启动

在 Windows 电脑安装 Python 3，将项目放在例如 `C:\AiCourse`。在 PowerShell 中执行：

```powershell
cd C:\AiCourse
py -m venv venv
.\venv\Scripts\python.exe -m pip install -r backend\requirements.txt

$env:JWT_SECRET_KEY = "填写固定的随机密钥"
$env:ADMIN_USERNAME = "admin"
$env:ADMIN_PASSWORD = "填写至少12位的密码"
.\venv\Scripts\uvicorn.exe main:app --app-dir backend --host 0.0.0.0 --port 8000
```

密钥可通过 `py -c "import secrets; print(secrets.token_urlsafe(48))"` 生成。请保存在电脑上，后续启动使用相同的值；不要提交到 Git。上述环境变量仅在当前 PowerShell 窗口有效，关闭窗口后服务停止。

先在部署电脑访问 `http://127.0.0.1:8000/api/health`。然后在**管理员 PowerShell** 中运行：

```powershell
New-NetFirewallRule -DisplayName "AiCourse LAN" -Direction Inbound -Action Allow -Protocol TCP -LocalPort 8000 -RemoteAddress LocalSubnet
ipconfig
```

找到当前网络连接的 IPv4 地址，例如 `192.168.10.25`，让同一局域网的手机访问 `http://192.168.10.25:8000`。创建小组二维码时也从这个局域网地址打开网站，避免二维码指向 `localhost`。如果校园网络隔离了设备或划分了不同子网，请联系网管检查互访规则。

试用期间先使用测试数据；HTTP 连接没有加密，录入真实学生信息前应配置校园内网 HTTPS。请定期备份 `data/practice_classroom.db` 和 `uploads/`。这两个目录包含本地数据，不会推送到 Git；新设备从仓库克隆后会自动创建空数据库和上传目录。
