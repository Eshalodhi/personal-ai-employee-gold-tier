@echo off
REM ============================================================
REM  AI Employee Vault — Gmail Inbox Watcher
REM  Launched by Windows Task Scheduler at system startup.
REM  Polls Gmail every 5 minutes. Runs indefinitely.
REM  See TASK_SCHEDULER_SETUP.md for registration instructions.
REM ============================================================

cd /d "D:\coding\Hackaton\hac_0\AI_Employee_Vault"

set YEAR=%DATE:~10,4%
set MON=%DATE:~4,2%
set DAY=%DATE:~7,2%
set LOGFILE=Logs\gmail_watcher_%YEAR%-%MON%-%DAY%.log

if not exist "Logs" mkdir Logs

echo [%DATE% %TIME%] ============================================ >> "%LOGFILE%"
echo [%DATE% %TIME%] Gmail Watcher starting                        >> "%LOGFILE%"
echo [%DATE% %TIME%] Vault: %CD%                                   >> "%LOGFILE%"
echo [%DATE% %TIME%] Poll interval: 300 seconds (5 minutes)        >> "%LOGFILE%"
echo [%DATE% %TIME%] ============================================ >> "%LOGFILE%"

"C:\Users\Esha Khan\AppData\Local\Programs\Python\Python314\python.exe" ^
    -u gmail_watcher.py >> "%LOGFILE%" 2>&1

set EXIT_CODE=%ERRORLEVEL%
echo [%DATE% %TIME%] Gmail Watcher exited with code: %EXIT_CODE%   >> "%LOGFILE%"
echo [%DATE% %TIME%] ============================================ >> "%LOGFILE%"

exit /b %EXIT_CODE%
