$ErrorActionPreference = 'Stop'

Write-Host 'Starting CareConnect API on http://localhost:8000'
Start-Process powershell -ArgumentList '-NoExit', '-Command', 'Set-Location backend; .\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8000'

Write-Host 'Starting CareConnect frontend on http://localhost:5173'
Start-Process powershell -ArgumentList '-NoExit', '-Command', 'Set-Location frontend; npm run dev -- --host 0.0.0.0'
