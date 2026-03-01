@echo off
:: ============================================================
:: AI Employee Vault — Morning Briefing
:: ============================================================
:: Scheduled Task: Daily at 8:00 AM
:: Purpose: Generate a morning briefing summarising pending
::          tasks and recent emails so the employee starts
::          the day with full situational awareness.
::
:: Task Scheduler settings (see CREATE_TASKS.md):
::   Trigger  : Daily, 08:00 AM
::   Action   : Run this .bat file
::   Start in : D:\coding\hackaton\hac_0\AI_Employee_Vault
:: ============================================================

:: ── Configuration ──────────────────────────────────────────
set VAULT_DIR=D:\coding\hackaton\hac_0\AI_Employee_Vault
set LOG_DIR=%VAULT_DIR%\scheduled_tasks\logs
set TASK_NAME=morning_briefing
set TIMESTAMP=%DATE:~10,4%-%DATE:~4,2%-%DATE:~7,2%_%TIME:~0,2%-%TIME:~3,2%
:: Remove any leading space from hour (e.g. " 8" → "08")
set TIMESTAMP=%TIMESTAMP: =0%
set LOG_FILE=%LOG_DIR%\%TASK_NAME%_%TIMESTAMP%.log

:: ── Pre-flight: ensure directories exist ───────────────────
if not exist "%LOG_DIR%" mkdir "%LOG_DIR%"
if not exist "%VAULT_DIR%" (
    echo [ERROR] Vault directory not found: %VAULT_DIR% >> "%LOG_FILE%"
    echo [ERROR] Vault directory not found: %VAULT_DIR%
    exit /b 1
)

:: ── Move to vault root (required for Claude context) ───────
cd /d "%VAULT_DIR%"
if errorlevel 1 (
    echo [ERROR] Failed to change to vault directory >> "%LOG_FILE%"
    exit /b 1
)

:: ── Header in log ──────────────────────────────────────────
echo ============================================================ >> "%LOG_FILE%"
echo  AI Employee — Morning Briefing                              >> "%LOG_FILE%"
echo  Started : %DATE% %TIME%                                     >> "%LOG_FILE%"
echo  Log file: %LOG_FILE%                                        >> "%LOG_FILE%"
echo ============================================================ >> "%LOG_FILE%"

:: ── Run Claude command ─────────────────────────────────────
echo [INFO] Running morning briefing claude command...
echo [INFO] Running morning briefing claude command... >> "%LOG_FILE%"

claude "Generate morning briefing with pending tasks and recent emails" >> "%LOG_FILE%" 2>&1
set CLAUDE_EXIT=%ERRORLEVEL%

:: ── Result handling ────────────────────────────────────────
echo. >> "%LOG_FILE%"
echo ============================================================ >> "%LOG_FILE%"
if %CLAUDE_EXIT% equ 0 (
    echo  Result  : SUCCESS >> "%LOG_FILE%"
    echo [SUCCESS] Morning briefing completed. See %LOG_FILE%
) else (
    echo  Result  : FAILED (exit code %CLAUDE_EXIT%) >> "%LOG_FILE%"
    echo [ERROR] Morning briefing failed with exit code %CLAUDE_EXIT%. See %LOG_FILE%
)
echo  Finished: %DATE% %TIME% >> "%LOG_FILE%"
echo ============================================================ >> "%LOG_FILE%"

:: ── Rotate old logs (keep last 30 days) ────────────────────
forfiles /p "%LOG_DIR%" /m "%TASK_NAME%_*.log" /d -30 /c "cmd /c del @path" 2>nul

exit /b %CLAUDE_EXIT%
