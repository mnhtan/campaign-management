# Quick status check for Google News Crawler

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "     QUICK CRAWLER STATUS CHECK" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

# Check task status
Write-Host "`nTask Status:" -ForegroundColor Yellow
try {
    $task = Get-ScheduledTask -TaskName "GoogleNewsCrawler" -ErrorAction Stop
    $taskInfo = Get-ScheduledTaskInfo -TaskName "GoogleNewsCrawler"
    
    Write-Host "Status: $($task.State)" -ForegroundColor $(if($task.State -eq "Ready") {"Green"} else {"Red"})
    Write-Host "Last Run: $($taskInfo.LastRunTime)" -ForegroundColor White
    Write-Host "Next Run: $($taskInfo.NextRunTime)" -ForegroundColor White
    
    # Time until next run
    if ($taskInfo.NextRunTime) {
        $timeUntilNext = $taskInfo.NextRunTime - (Get-Date)
        if ($timeUntilNext.TotalMinutes -gt 0) {
            Write-Host "Next run in: $([math]::Round($timeUntilNext.TotalMinutes)) minutes" -ForegroundColor Green
        } else {
            Write-Host "Overdue or running now" -ForegroundColor Orange
        }
    }
} catch {
    Write-Host "Task NOT FOUND!" -ForegroundColor Red
}

# Check batch files
Write-Host "`nBatch Files:" -ForegroundColor Yellow
if (Test-Path "../batches") {
    $batchFiles = Get-ChildItem "../batches" -Filter "batch_*.csv"
    if ($batchFiles) {
        $latest = $batchFiles | Sort-Object LastWriteTime -Descending | Select-Object -First 1
        $timeSince = (Get-Date) - $latest.LastWriteTime
        
        Write-Host "Total batches: $($batchFiles.Count)" -ForegroundColor Green
        Write-Host "Latest batch: $($latest.Name)" -ForegroundColor White
        Write-Host "Created: $([math]::Round($timeSince.TotalMinutes)) minutes ago" -ForegroundColor White
        
        # Today's batches
        $today = Get-Date -Format "yyyyMMdd"
        $todayBatches = $batchFiles | Where-Object { $_.Name -match "batch_${today}_" }
        Write-Host "Today's batches: $($todayBatches.Count)" -ForegroundColor Green
    } else {
        Write-Host "No batch files yet" -ForegroundColor Yellow
    }
} else {
    Write-Host "Batches folder not created yet" -ForegroundColor Yellow
}

Write-Host "`n========================================" -ForegroundColor Cyan 