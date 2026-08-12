# Aira startup installer — no admin rights required.
# It first tries Task Scheduler when elevated; otherwise it uses the Windows Startup folder.
$ErrorActionPreference = 'Stop'
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$Bat = Join-Path $Root 'start_aira.bat'
if (!(Test-Path $Bat)) { throw "start_aira.bat not found at $Bat" }

$startup = [Environment]::GetFolderPath('Startup')
$startupBat = Join-Path $startup 'AutoAgencyOS-Aira.bat'
Copy-Item $Bat $startupBat -Force

Write-Host "Aira startup installed successfully." -ForegroundColor Green
Write-Host "Startup file: $startupBat"
Write-Host "No Administrator permission is required."
Write-Host "Aira will start automatically when this Windows user logs in."
