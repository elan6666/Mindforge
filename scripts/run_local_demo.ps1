$ErrorActionPreference = "Stop"

$env:PYTHONPATH = (Resolve-Path ".").Path

if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    throw "python command not found."
}

Write-Host "Starting Multi-Agent Assistant backend on http://127.0.0.1:8000"
python -m uvicorn app.backend.main:app --host 127.0.0.1 --port 8000 --reload

