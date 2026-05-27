@echo off
chcp 65001 >nul
cd /d "%~dp0"

echo Stopping old bot processes...
powershell -NoProfile -Command "Get-CimInstance Win32_Process -Filter \"Name='python.exe'\" | Where-Object { $_.CommandLine -like '*main.py*' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }"
timeout /t 2 /nobreak >nul 2>nul

echo Starting DeskMate bot...
call venv\Scripts\activate.bat
python main.py
pause
