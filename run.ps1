# BADA 로컬 실행 (PowerShell). BADA 폴더에서: .\run.ps1
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

if (-not (Test-Path ".venv")) {
  Write-Host "[run] venv 생성..." -ForegroundColor Cyan
  python -m venv .venv
}
. .\.venv\Scripts\Activate.ps1

Write-Host "[run] 의존성 설치..." -ForegroundColor Cyan
pip install -q -r backend/requirements.txt

Set-Location backend
Write-Host "[run] 서버 시작: http://localhost:8000 (빈 상태에서 새 사건부터 시작)" -ForegroundColor Green
uvicorn app.main:app --reload
