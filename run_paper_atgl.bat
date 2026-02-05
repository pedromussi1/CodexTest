@echo off
setlocal
cd /d "d:\Codex Projects\AI-trading\CodexTest"
if not exist logs mkdir logs
set "LOGFILE=logs\atgl_%date:~10,4%-%date:~4,2%-%date:~7,2%.log"
call .\.venv\Scripts\Activate.ps1
python -m src.paper_atgl --universe dynamic --max-symbols 200 --live --summary-file latest_summary.txt --email >> "%LOGFILE%" 2>&1
endlocal
