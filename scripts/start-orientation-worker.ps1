$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $projectRoot
& "$projectRoot\venv\Scripts\python.exe" -m celery -A consultations.intake_worker:app worker --pool=solo --concurrency=1 --loglevel=WARNING --without-gossip --without-mingle --without-heartbeat
