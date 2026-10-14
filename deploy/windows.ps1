# Install and run AiCourse at Windows startup for LAN testing.
# Run once from an Administrator PowerShell window.
$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$identity = [Security.Principal.WindowsIdentity]::GetCurrent()
$principal = [Security.Principal.WindowsPrincipal]::new($identity)
if (-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    throw '请在“以管理员身份运行”的 PowerShell 中执行此脚本。'
}

$projectDir = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
if ($projectDir.StartsWith('\\')) {
    throw '请将项目放在本机磁盘，不能从网络共享目录部署。'
}
Set-Location $projectDir
$python = Join-Path $projectDir 'venv\Scripts\python.exe'
if (-not (Test-Path $python)) {
    if (Get-Command py -ErrorAction SilentlyContinue) {
        & py -3 -m venv venv
    } elseif (Get-Command python -ErrorAction SilentlyContinue) {
        & python -m venv venv
    } else {
        throw '未找到 Python 3，请先安装 Python。'
    }
    if ($LASTEXITCODE -ne 0) { throw '创建 Python 虚拟环境失败。' }
}

& $python -m pip install -r backend\requirements.txt
if ($LASTEXITCODE -ne 0) { throw '安装 Python 依赖失败。' }
$envPath = Join-Path $projectDir '.env'
& $python deploy\configure_env.py $envPath
if ($LASTEXITCODE -ne 0) { throw '创建配置失败。' }

# Limit the stored administrator password to local administrators and the task account.
& icacls.exe $envPath /inheritance:r /grant:r '*S-1-5-18:(F)' '*S-1-5-32-544:(F)' | Out-Null
if ($LASTEXITCODE -ne 0) { throw '设置配置文件权限失败。' }

$taskName = 'AiCourse'
$action = New-ScheduledTaskAction -Execute $python `
    -Argument '-m uvicorn main:app --app-dir backend --env-file .env --host 0.0.0.0 --port 8000' `
    -WorkingDirectory $projectDir
$trigger = New-ScheduledTaskTrigger -AtStartup
$taskPrincipal = New-ScheduledTaskPrincipal -UserId 'SYSTEM' -LogonType ServiceAccount -RunLevel Highest
$settings = New-ScheduledTaskSettingsSet -ExecutionTimeLimit (New-TimeSpan -Seconds 0) `
    -RestartCount 3 -RestartInterval (New-TimeSpan -Minutes 1) `
    -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries
Register-ScheduledTask -TaskName $taskName -Action $action -Trigger $trigger `
    -Principal $taskPrincipal -Settings $settings -Force | Out-Null

$ruleName = 'AiCourse LAN 8000'
$existingRule = Get-NetFirewallRule -DisplayName $ruleName -ErrorAction SilentlyContinue
if ($existingRule) { $existingRule | Remove-NetFirewallRule }
New-NetFirewallRule -DisplayName $ruleName -Direction Inbound -Action Allow `
    -Protocol TCP -LocalPort 8000 -RemoteAddress LocalSubnet | Out-Null

Stop-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue
Start-ScheduledTask -TaskName $taskName
$healthy = $false
for ($attempt = 0; $attempt -lt 10; $attempt++) {
    Start-Sleep -Seconds 1
    try {
        $result = Invoke-RestMethod -Uri 'http://127.0.0.1:8000/api/health' -TimeoutSec 2
        if ($result.status -eq 'ok') { $healthy = $true; break }
    } catch { }
}
if (-not $healthy) {
    throw '服务未通过健康检查，请在“任务计划程序”中检查 AiCourse 任务的运行状态。'
}
Write-Host '部署完成。请用 ipconfig 查找本机 IPv4 地址，然后访问 http://<本机IP>:8000'
Write-Host '重新部署：再次运行此脚本。停止服务：Stop-ScheduledTask -TaskName AiCourse'
