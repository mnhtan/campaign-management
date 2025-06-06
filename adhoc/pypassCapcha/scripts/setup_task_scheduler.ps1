# Script setup Windows Task Scheduler cho Google News Crawler

# Lay thong tin thu muc hien tai
$currentDir = Get-Location
$pythonScript = Join-Path $currentDir "code\pypassCapcha.py"
$batFile = Join-Path $currentDir "run_scheduled_crawler.bat"

Write-Host "GOOGLE NEWS CRAWLER - TASK SCHEDULER SETUP" -ForegroundColor Yellow
Write-Host ("=" * 60) -ForegroundColor Yellow

# Kiem tra file Python co ton tai khong
if (-not (Test-Path $pythonScript)) {
    Write-Host "File pypassCapcha.py khong tim thay!" -ForegroundColor Red
    Write-Host "Duong dan: $pythonScript" -ForegroundColor Red
    exit 1
}

# Tao file .bat
$batContent = @"
@echo off
cd /d "$currentDir\code"
python "pypassCapcha.py" --scheduled
echo.
echo Batch completed at %date% %time%
pause
"@

$batContent | Out-File -FilePath $batFile -Encoding UTF8
Write-Host "Created batch file: $batFile" -ForegroundColor Green

# Thong tin task
$taskName = "GoogleNewsCrawler"
$taskDescription = "Google News Crawler - Crawl every 1 hour from activation until stopped"

Write-Host ""
Write-Host "Setting up Windows Task Scheduler..." -ForegroundColor Cyan

try {
    # Xoa task cu neu co
    $existingTask = Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue
    if ($existingTask) {
        Write-Host "Found existing task. Removing..." -ForegroundColor Yellow
        Unregister-ScheduledTask -TaskName $taskName -Confirm:$false
    }

    # Tao action
    $action = New-ScheduledTaskAction -Execute $batFile

    # Tao trigger - chay ngay lap tuc va repeat moi 1 tieng trong 365 ngay
    $startTime = (Get-Date).AddMinutes(2)  # Bat dau sau 2 phut
    $trigger = New-ScheduledTaskTrigger -Once -At $startTime -RepetitionInterval (New-TimeSpan -Hours 1) -RepetitionDuration (New-TimeSpan -Days 365)

    # Cau hinh settings
    $settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable

    # Tao principal (chay voi quyen user hien tai)
    $principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive

    # Dang ky task
    Register-ScheduledTask -TaskName $taskName -Action $action -Trigger $trigger -Settings $settings -Principal $principal -Description $taskDescription

    Write-Host "Task scheduler setup completed!" -ForegroundColor Green
    Write-Host ""
    Write-Host "TASK DETAILS:" -ForegroundColor Cyan
    Write-Host "Task Name: $taskName" -ForegroundColor White
    Write-Host "Schedule: Start in 2 minutes, then repeat every 1 hour indefinitely" -ForegroundColor White
    Write-Host "First run: $($startTime.ToString('yyyy-MM-dd HH:mm:ss'))" -ForegroundColor White
    Write-Host "Script: $batFile" -ForegroundColor White
    Write-Host ""
    Write-Host "Expected Results:" -ForegroundColor Cyan
    Write-Host "- 24 batches per day (every hour)" -ForegroundColor White
    Write-Host "- ~600 articles per batch (60 keywords x 10 articles)" -ForegroundColor White
    Write-Host "- ~14,400 articles per day total" -ForegroundColor White
    Write-Host ""
    Write-Host "Output files will be saved in: $currentDir\batches\" -ForegroundColor White

} catch {
    Write-Host "Error setting up task scheduler: $($_.Exception.Message)" -ForegroundColor Red
    Write-Host ""
    Write-Host "MANUAL SETUP INSTRUCTIONS:" -ForegroundColor Yellow
    Write-Host "1. Open Task Scheduler (taskschd.msc)" -ForegroundColor White
    Write-Host "2. Create Basic Task..." -ForegroundColor White
    Write-Host "3. Name: GoogleNewsCrawler" -ForegroundColor White
    Write-Host "4. Trigger: Once, start immediately" -ForegroundColor White
    Write-Host "5. Repeat every: 1 hour indefinitely" -ForegroundColor White
    Write-Host "6. Action: Start program" -ForegroundColor White
    Write-Host "7. Program: $batFile" -ForegroundColor White
}

Write-Host ""
Write-Host "TIP: You can test the batch file manually:" -ForegroundColor Yellow
Write-Host "Double-click: $batFile" -ForegroundColor White
Write-Host ""
Write-Host "To monitor results:" -ForegroundColor Yellow
Write-Host "Check folder: $currentDir\batches\" -ForegroundColor White
Write-Host ""
Write-Host "To stop the crawler:" -ForegroundColor Red
Write-Host "Open Task Scheduler -> Find 'GoogleNewsCrawler' -> Right-click -> Disable/Delete" -ForegroundColor White
Write-Host ""
Write-Host "Setup completed! The crawler will start in 2 minutes and run every hour until you stop it." -ForegroundColor Green

# Pause de user co the doc
Read-Host "Press Enter to exit" 