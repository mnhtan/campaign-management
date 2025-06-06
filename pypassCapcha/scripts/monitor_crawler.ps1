# Script monitoring Google News Crawler

function Show-CrawlerStatus {
    Clear-Host
    Write-Host ("=" * 60) -ForegroundColor Yellow
    Write-Host "GOOGLE NEWS CRAWLER - MONITORING DASHBOARD" -ForegroundColor Yellow
    Write-Host ("=" * 60) -ForegroundColor Yellow
    Write-Host ""
    
    # Kiem tra trang thai task
    Write-Host "TASK STATUS:" -ForegroundColor Cyan
    try {
        $task = Get-ScheduledTask -TaskName "GoogleNewsCrawler" -ErrorAction Stop
        $taskInfo = Get-ScheduledTaskInfo -TaskName "GoogleNewsCrawler"
        
        Write-Host "Task Name: GoogleNewsCrawler" -ForegroundColor White
        Write-Host "State: $($task.State)" -ForegroundColor $(if($task.State -eq "Ready") {"Green"} else {"Red"})
        Write-Host "Last Run Time: $($taskInfo.LastRunTime)" -ForegroundColor White
        Write-Host "Next Run Time: $($taskInfo.NextRunTime)" -ForegroundColor White
        Write-Host "Last Result: $($taskInfo.LastTaskResult)" -ForegroundColor $(if($taskInfo.LastTaskResult -eq 0) {"Green"} else {"Red"})
    }
    catch {
        Write-Host "Task not found or error: $($_.Exception.Message)" -ForegroundColor Red
    }
    
    Write-Host ""
    
    # Kiem tra batch files
    Write-Host "BATCH FILES:" -ForegroundColor Cyan
    $batchDir = "../batches"
    if (Test-Path $batchDir) {
        $batchFiles = Get-ChildItem $batchDir -Filter "batch_*.csv" | Sort-Object LastWriteTime -Descending
        
        if ($batchFiles) {
            Write-Host "Total batch files: $($batchFiles.Count)" -ForegroundColor Green
            Write-Host ""
            Write-Host "LATEST 10 BATCHES:" -ForegroundColor Yellow
            
            foreach ($file in $batchFiles | Select-Object -First 10) {
                $size = [math]::Round($file.Length / 1KB, 2)
                $timeAgo = (Get-Date) - $file.LastWriteTime
                $ageText = if ($timeAgo.TotalHours -lt 1) {
                    "$([math]::Round($timeAgo.TotalMinutes)) minutes ago"
                } else {
                    "$([math]::Round($timeAgo.TotalHours, 1)) hours ago"
                }
                
                Write-Host "  $($file.Name) - ${size}KB - $ageText" -ForegroundColor White
            }
        } else {
            Write-Host "No batch files found" -ForegroundColor Yellow
        }
    } else {
        Write-Host "Batches directory not found" -ForegroundColor Yellow
    }
    
    Write-Host ""
    
    # Tinh toan statistics
    if (Test-Path $batchDir) {
        Write-Host "STATISTICS:" -ForegroundColor Cyan
        $allBatches = Get-ChildItem $batchDir -Filter "batch_*.csv"
        if ($allBatches) {
            $totalSize = ($allBatches | Measure-Object Length -Sum).Sum
            $totalSizeMB = [math]::Round($totalSize / 1MB, 2)
            
            # Estimate articles (rough calculation)
            $estimatedArticles = $allBatches.Count * 600  # 600 articles per batch
            
            Write-Host "Total batches: $($allBatches.Count)" -ForegroundColor White
            Write-Host "Total data size: ${totalSizeMB} MB" -ForegroundColor White
            Write-Host "Estimated articles: $estimatedArticles" -ForegroundColor White
            
            # Batches today
            $today = Get-Date -Format "yyyyMMdd"
            $todayBatches = $allBatches | Where-Object { $_.Name -match "batch_${today}_" }
            Write-Host "Batches today: $($todayBatches.Count)" -ForegroundColor White
        }
    }
    
    Write-Host ""
    Write-Host ("=" * 60) -ForegroundColor Yellow
    Write-Host "CONTROLS:" -ForegroundColor Yellow
    Write-Host "D - Disable crawler | E - Enable crawler | Q - Quit" -ForegroundColor White
    Write-Host "R - Refresh | T - Test run | A - Analyze batches" -ForegroundColor White
    Write-Host ("=" * 60) -ForegroundColor Yellow
}

function Start-Monitoring {
    while ($true) {
        Show-CrawlerStatus
        
        $key = Read-Host "Choose action"
        
        switch ($key.ToUpper()) {
            'D' {
                Write-Host "Disabling crawler..." -ForegroundColor Yellow
                try {
                    Disable-ScheduledTask -TaskName "GoogleNewsCrawler" -ErrorAction Stop
                    Write-Host "Crawler disabled successfully!" -ForegroundColor Green
                } catch {
                    Write-Host "Error: $($_.Exception.Message)" -ForegroundColor Red
                }
                Start-Sleep 2
            }
            'E' {
                Write-Host "Enabling crawler..." -ForegroundColor Yellow
                try {
                    Enable-ScheduledTask -TaskName "GoogleNewsCrawler" -ErrorAction Stop
                    Write-Host "Crawler enabled successfully!" -ForegroundColor Green
                } catch {
                    Write-Host "Error: $($_.Exception.Message)" -ForegroundColor Red
                }
                Start-Sleep 2
            }
                         'T' {
                 Write-Host "Running test..." -ForegroundColor Yellow
                 Set-Location "../code"
                 python "pypassCapcha.py" --test
                 Set-Location "../scripts"
                 Read-Host "Press Enter to continue"
             }
                         'A' {
                 Write-Host "Analyzing batches..." -ForegroundColor Yellow
                 Set-Location "../code"
                 python "analyze_batches.py"
                 Set-Location "../scripts"
                 Read-Host "Press Enter to continue"
             }
            'R' {
                # Just refresh - continue loop
            }
            'Q' {
                Write-Host "Exiting monitoring..." -ForegroundColor Yellow
                return
            }
            default {
                Write-Host "Invalid option!" -ForegroundColor Red
                Start-Sleep 1
            }
        }
    }
}

# Start monitoring
Start-Monitoring 