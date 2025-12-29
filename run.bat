@echo off
title Mission RBI Launcher

cd /d %~dp0

REM Activate venv
call venv\Scripts\activate

REM Ensure dependencies
pip install -r requirements.txt >nul 2>&1

REM Start Flask in background (no window)
start /b python app.py

REM Give Flask time to boot
timeout /t 5 >nul

REM Start Cloudflare tunnel in background, log output
start /b cloudflared tunnel --url http://localhost:5000 > tunnel.log 2>&1

REM Start Telegram watcher in background
start /b python watch_tunnel.py

REM Launcher done – close silently
exit
