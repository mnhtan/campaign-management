# GOOGLE NEWS CRAWLER - QUICK COMMANDS
# Copy từng lệnh để chạy

Write-Host "========================================" -ForegroundColor Green
Write-Host "   GOOGLE NEWS CRAWLER COMMANDS" -ForegroundColor Green  
Write-Host "========================================" -ForegroundColor Green

Write-Host "`n STOP/START COMMANDS:" -ForegroundColor Red
Write-Host "# Stop crawler:"
Write-Host 'Disable-ScheduledTask -TaskName "GoogleNewsCrawler"' -ForegroundColor Yellow

Write-Host "`n# Start crawler:"
Write-Host 'Enable-ScheduledTask -TaskName "GoogleNewsCrawler"' -ForegroundColor Yellow

Write-Host "`n# Delete crawler completely:"
Write-Host 'Unregister-ScheduledTask -TaskName "GoogleNewsCrawler" -Confirm:$false' -ForegroundColor Yellow

Write-Host "`n MONITORING COMMANDS:" -ForegroundColor Blue
Write-Host "# Quick status check:"
Write-Host 'powershell -ExecutionPolicy Bypass -File "quick_check.ps1"' -ForegroundColor Yellow

Write-Host "`n# Full monitoring dashboard:"
Write-Host 'powershell -ExecutionPolicy Bypass -File "monitor_crawler.ps1"' -ForegroundColor Yellow

Write-Host "`n# Check task details:"
Write-Host 'Get-ScheduledTask -TaskName "GoogleNewsCrawler" | fl' -ForegroundColor Yellow
Write-Host 'Get-ScheduledTaskInfo -TaskName "GoogleNewsCrawler" | fl' -ForegroundColor Yellow

Write-Host "`n FILE MONITORING:" -ForegroundColor Magenta
Write-Host "# List batch files:"
Write-Host 'Get-ChildItem "../batches" -Filter "batch_*.csv" | Sort-Object LastWriteTime -Descending' -ForegroundColor Yellow

Write-Host "`n# Count today's batches:"
Write-Host '$today = Get-Date -Format "yyyyMMdd"' -ForegroundColor Yellow
Write-Host 'Get-ChildItem "../batches" -Filter "batch_${today}_*.csv" | Measure-Object' -ForegroundColor Yellow

Write-Host "`n# Watch batches folder (real-time):"
Write-Host 'Get-ChildItem "../batches" -Filter "batch_*.csv" | Sort-Object LastWriteTime -Descending | Select-Object -First 5 | Format-Table Name,Length,LastWriteTime' -ForegroundColor Yellow

Write-Host "`n TESTING COMMANDS:" -ForegroundColor Cyan
Write-Host "# Test manual crawl:"
Write-Host 'cd ../code; python pypassCapcha.py --test; cd ../scripts' -ForegroundColor Yellow

Write-Host "`n# Analyze batch results:"
Write-Host 'cd ../code; python analyze_batches.py; cd ../scripts' -ForegroundColor Yellow

Write-Host "`n# Check log files:"
Write-Host 'Get-Content "logs/crawler.log" -Tail 20' -ForegroundColor Yellow

Write-Host "`n========================================" -ForegroundColor Green
Write-Host "Copy lệnh cần thiết và paste vào PowerShell!" -ForegroundColor White
Write-Host "========================================" -ForegroundColor Green 