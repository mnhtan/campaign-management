@echo off
cd /d "scripts"
powershell -ExecutionPolicy Bypass -File "monitor_crawler.ps1"
pause 