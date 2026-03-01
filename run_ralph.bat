@echo off
REM ============================================================
REM  AI Employee Vault — Ralph Wiggum Autonomous Loop
REM  Launched by Windows Task Scheduler at system startup.
REM  See TASK_SCHEDULER_SETUP.md for registration instructions.
REM ============================================================

cd /d "D:\coding\Hackaton\hac_0\AI_Employee_Vault"

REM Build a dated log filename (YYYY-MM-DD format from %DATE%)
set YEAR=%DATE:~10,4%
set MON=%DATE:~4,2%
set DAY=%DATE:~7,2%
set LOGFILE=Logs\ralph_%YEAR%-%MON%-%DAY%.log

REM Ensure Logs directory exists
if not exist "Logs" mkdir Logs

echo [%DATE% %TIME%] ============================================ >> "%LOGFILE%"
echo [%DATE% %TIME%] Ralph Wiggum Loop starting (PID: N/A)        >> "%LOGFILE%"
echo [%DATE% %TIME%] Vault: %CD%                                   >> "%LOGFILE%"
echo [%DATE% %TIME%] ============================================ >> "%LOGFILE%"

REM -u = unbuffered output so log file updates in real time
"C:\Users\Esha Khan\AppData\Local\Programs\Python\Python314\python.exe" ^
    -u ralph_wiggum_loop.py >> "%LOGFILE%" 2>&1

set EXIT_CODE=%ERRORLEVEL%
echo [%DATE% %TIME%] Ralph exited with code: %EXIT_CODE%           >> "%LOGFILE%"
echo [%DATE% %TIME%] ============================================ >> "%LOGFILE%"

REM Exit with Python's exit code so Task Scheduler can detect failures
exit /b %EXIT_CODE%
