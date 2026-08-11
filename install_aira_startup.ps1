$Project = "C:\AutoAgencyOS"
$Bat = Join-Path $Project "start_aira.bat"
$Action = New-ScheduledTaskAction -Execute $Bat
$Trigger = New-ScheduledTaskTrigger -AtLogOn
$Principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive -RunLevel Highest
$Settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -RestartCount 999 -RestartInterval (New-TimeSpan -Minutes 1)
Register-ScheduledTask -TaskName "Aira AutoAgencyOS" -Action $Action -Trigger $Trigger -Principal $Principal -Settings $Settings -Force
Write-Host "Aira startup task installed."
