@echo off
:: ============================================================
:: AI Employee Vault — Daily Summary
:: ============================================================
:: Scheduled Task: Daily at 8:00 PM
:: Purpose: Generate an end-of-day summary with statistics
::          and update the Dashboard so the employee (and
::          human) has a clean record of the day's work.
::
:: Task Scheduler settings (see CREATE_TASKS.md):
::   Trigger  : Daily, 08:00 PM (20:00)
::   Action   : Run this .bat file
::   Start in : D:\coding\hackaton\hac_0\AI_Employee_Vault
:: ============================================================

:: ── Configuration ──────────────────────────────────────────
set VAULT_DIR=D:\coding\hackaton\hac_0\AI_Employee_Vault
set LOG_DIR=%VAULT_DIR%\scheduled_tasks\logs
set TASK_NAME=daily_summary
set TIMESTAMP=%DATE:~10,4%-%DATE:~4,2%-%DATE:~7,2%_%TIME:~0,2%-%TIME:~3,2%
set TIMESTAMP=%TIMESTAMP: =0%
set LOG_FILE=%LOG_DIR%\%TASK_NAME%_%TIMESTAMP%.log

:: ── Pre-flight: ensure directories exist ───────────────────
if not exist "%LOG_DIR%" mkdir "%LOG_DIR%"
if not exist "%VAULT_DIR%" (
    echo [ERROR] Vault directory not found: %VAULT_DIR% >> "%LOG_FILE%"
    echo [ERROR] Vault directory not found: %VAULT_DIR%
    exit /b 1
)

:: ── Move to vault root ─────────────────────────────────────
cd /d "%VAULT_DIR%"
if errorlevel 1 (
    echo [ERROR] Failed to change to vault directory >> "%LOG_FILE%"
    exit /b 1
)

:: ── Header in log ──────────────────────────────────────────
echo ============================================================ >> "%LOG_FILE%"
echo  AI Employee — Daily Summary                                 >> "%LOG_FILE%"
echo  Started : %DATE% %TIME%                                     >> "%LOG_FILE%"
echo  Log file: %LOG_FILE%                                        >> "%LOG_FILE%"
echo ============================================================ >> "%LOG_FILE%"

:: ── Run Claude command ─────────────────────────────────────
echo [INFO] Running daily summary claude command...
echo [INFO] Running daily summary claude command... >> "%LOG_FILE%"

claude "Create end-of-day summary with stats and update Dashboard" >> "%LOG_FILE%" 2>&1
set CLAUDE_EXIT=%ERRORLEVEL%

:: ── Result handling ────────────────────────────────────────
echo. >> "%LOG_FILE%"
echo ============================================================ >> "%LOG_FILE%"
if %CLAUDE_EXIT% equ 0 (
    echo  Result  : SUCCESS >> "%LOG_FILE%"
    echo [SUCCESS] Daily summary completed. See %LOG_FILE%
) else (
    echo  Result  : FAILED (exit code %CLAUDE_EXIT%) >> "%LOG_FILE%"
    echo [ERROR] Daily summary failed with exit code %CLAUDE_EXIT%. See %LOG_FILE%
)
echo  Finished: %DATE% %TIME% >> "%LOG_FILE%"
echo ============================================================ >> "%LOG_FILE%"

:: ── Rotate old logs (keep last 30 days) ────────────────────
forfiles /p "%LOG_DIR%" /m "%TASK_NAME%_*.log" /d -30 /c "cmd /c del @path" 2>nul

exit /b %CLAUDE_EXIT%
