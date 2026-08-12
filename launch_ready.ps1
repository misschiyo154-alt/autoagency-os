$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot
Write-Host 'AutoAgencyOS preflight' -ForegroundColor Cyan
& .\.venv\Scripts\python.exe -m py_compile .\run.py .\telegram_bot.py .\04-emails\generate_email.py .\04-emails\send_email.py .\08-scripts\scrape_leads.py .\08-scripts\enrich_leads.py .\08-scripts\generate_website.py
if ($LASTEXITCODE -ne 0) { throw 'Python syntax check failed.' }
if (!(Test-Path '.\.env')) { Write-Warning '.env missing. Copy .env.example and add Telegram/Gemini/Groq/SMTP credentials.' }
Write-Host 'Syntax: OK' -ForegroundColor Green
Write-Host 'Starting Aira...' -ForegroundColor Green
& .\.venv\Scripts\python.exe .\telegram_bot.py
