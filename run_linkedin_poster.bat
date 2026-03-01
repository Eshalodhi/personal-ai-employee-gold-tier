@echo off
REM ============================================================
REM  AI Employee Vault — LinkedIn Auto-Poster
REM  Launched by Windows Task Scheduler Mon/Wed/Fri at 10:00.
REM  Uses --ralph-check (smart mode): posts only if conditions
REM  are met, processes any pending approvals, then exits.
REM  See TASK_SCHEDULER_SETUP.md for registration instructions.
REM ============================================================

cd /d "D:\coding\Hackaton\hac_0\AI_Employee_Vault"

set YEAR=%DATE:~10,4%
set MON=%DATE:~4,2%
set DAY=%DATE:~7,2%
set LOGFILE=Logs\linkedin_%YEAR%-%MON%-%DAY%.log

if not exist "Logs" mkdir Logs

echo [%DATE% %TIME%] ============================================ >> "%LOGFILE%"
echo [%DATE% %TIME%] LinkedIn Auto-Poster starting (ralph-check)  >> "%LOGFILE%"
echo [%DATE% %TIME%] Date: %YEAR%-%MON%-%DAY%                    >> "%LOGFILE%"
echo [%DATE% %TIME%] ============================================ >> "%LOGFILE%"

"C:\Users\Esha Khan\AppData\Local\Programs\Python\Python314\python.exe" ^
    -u linkedin_auto_poster.py --ralph-check >> "%LOGFILE%" 2>&1

set EXIT_CODE=%ERRORLEVEL%

if %EXIT_CODE% EQU 0 (
    echo [%DATE% %TIME%] LinkedIn check completed successfully      >> "%LOGFILE%"
) else (
    echo [%DATE% %TIME%] LinkedIn check FAILED code: %EXIT_CODE%   >> "%LOGFILE%"
)

echo [%DATE% %TIME%] ============================================ >> "%LOGFILE%"

exit /b %EXIT_CODE%
