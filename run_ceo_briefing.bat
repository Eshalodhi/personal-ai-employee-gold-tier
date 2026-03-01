@echo off
REM ============================================================
REM  AI Employee Vault — Weekly CEO Briefing Generator
REM  Launched by Windows Task Scheduler every Sunday at 08:00.
REM  Generates Reports/CEO_Briefing_YYYY-MM-DD.md and exits.
REM  See TASK_SCHEDULER_SETUP.md for registration instructions.
REM ============================================================

cd /d "D:\coding\Hackaton\hac_0\AI_Employee_Vault"

set YEAR=%DATE:~10,4%
set MON=%DATE:~4,2%
set DAY=%DATE:~7,2%
set LOGFILE=Logs\ceo_briefing_%YEAR%-%MON%-%DAY%.log

if not exist "Logs" mkdir Logs
if not exist "Reports" mkdir Reports

echo [%DATE% %TIME%] ============================================ >> "%LOGFILE%"
echo [%DATE% %TIME%] CEO Briefing Generator starting              >> "%LOGFILE%"
echo [%DATE% %TIME%] Week ending: %YEAR%-%MON%-%DAY%             >> "%LOGFILE%"
echo [%DATE% %TIME%] Output dir: Reports\                         >> "%LOGFILE%"
echo [%DATE% %TIME%] ============================================ >> "%LOGFILE%"

"C:\Users\Esha Khan\AppData\Local\Programs\Python\Python314\python.exe" ^
    -u weekly_ceo_briefing.py >> "%LOGFILE%" 2>&1

set EXIT_CODE=%ERRORLEVEL%

if %EXIT_CODE% EQU 0 (
    echo [%DATE% %TIME%] CEO Briefing completed successfully        >> "%LOGFILE%"
) else (
    echo [%DATE% %TIME%] CEO Briefing FAILED with code: %EXIT_CODE% >> "%LOGFILE%"
    echo [%DATE% %TIME%] Check log above for Python traceback        >> "%LOGFILE%"
)

echo [%DATE% %TIME%] ============================================ >> "%LOGFILE%"

exit /b %EXIT_CODE%
