# 本机 Westlake 模拟环境（Python 3.12 + numpy<2）
# 在项目根目录 PowerShell 执行: .\scripts\setup_westlake_local.ps1

$ErrorActionPreference = "Stop"
$Py312 = "C:\Users\ROG\AppData\Local\Programs\Python\Python312\python.exe"
$WestlakeTutorial = "C:\Users\ROG\westlake-tutorial"
$RepoRoot = Split-Path -Parent $PSScriptRoot

if (-not (Test-Path $Py312)) {
    Write-Host "未找到 Python 3.12: $Py312"
    Write-Host "请安装 Python 3.12 或修改本脚本中的 `$Py312 路径。"
    exit 1
}

Write-Host "使用: $Py312"
& $Py312 -m pip install --upgrade pip
& $Py312 -m pip install -r (Join-Path $RepoRoot "requirements-westlake-sim.txt")

if (Test-Path (Join-Path $WestlakeTutorial "westlake")) {
    & $Py312 -m pip install -e (Join-Path $WestlakeTutorial "westlake")
} else {
    Write-Host "未找到 westlake 源码目录，跳过 pip install -e。请手动安装 westlake。"
}

& $Py312 -c "import westlake, numpy; print('westlake OK, numpy', numpy.__version__)"

Write-Host ""
Write-Host "请在 config.yaml 的 nautilus.python 中写入:"
Write-Host "  python: `"$($Py312 -replace '\\','/')`""
