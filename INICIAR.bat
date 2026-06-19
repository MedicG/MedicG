@echo off
cd /d "%~dp0"
set HOST=0.0.0.0
set PORT=8080
python server.py
pause
