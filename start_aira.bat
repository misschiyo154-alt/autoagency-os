@echo off
cd /d C:\AutoAgencyOS
if not exist ".venv\Scripts\python.exe" exit /b 1
start "Aira" /min cmd /c ".venv\Scripts\python.exe telegram_bot.py >> aira.log 2>&1"
