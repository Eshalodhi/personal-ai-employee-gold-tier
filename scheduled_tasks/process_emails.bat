@echo off
:: ============================================================
:: AI Employee Vault — Process Emails
:: ============================================================
:: Scheduled Task: Every 2 hours
:: Purpose: Process all pending email tasks sitting in
::          Needs_Action/ using FILE_PROCESSOR_SKILL so no
::          email waits more than 2 hours for triage.
::
:: Task Scheduler settings (see CREATE_TASKS.md):
::   Trigger  : Daily, 06:00 AM, repeat every 2 hours
::              for a duration of 18 hours (or "indefinitely")
::   Action   : Run this .bat file
::   Start in : D:\coding\hackaton\hac_0\AI_Employee_Vault
:: ============================================================

:: ── Configuration ──────────────────────────────────────────
set VAULT_DIR=D:\coding\hackaton\hac_0\AI_Employee_Vault
set LOG_DIR=%VAULT_DIR%\scheduled_tasks\logs
set TASK_NAME=process_emails
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

:: ── Check for pending emails before running ─────────────────
:: (Avoids spawning Claude when there's nothing to process)
set NEEDS_ACTION_DIR=%VAULT_DIR%\Needs_Action
set EMAIL_COUNT=0
for %%f in ("%NEEDS_ACTION_DIR%\EMAIL_*.md") do set /a EMAIL_COUNT+=1

:: ── Move to vault root ─────────────────────────────────────
cd /d "%VAULT_DIR%"
if errorlevel 1 (
    echo [ERROR] Failed to change to vault directory >> "%LOG_FILE%"
    exit /b 1
)

:: ── Header in log ──────────────────────────────────────────
echo ============================================================ >> "%LOG_FILE%"
echo  AI Employee — Process Emails                                >> "%LOG_FILE%"
echo  Started : %DATE% %TIME%                                     >> "%LOG_FILE%"
echo  Pending : %EMAIL_COUNT% email task(s) in Needs_Action/     >> "%LOG_FILE%"
echo  Log file: %LOG_FILE%                                        >> "%LOG_FILE%"
echo ============================================================ >> "%LOG_FILE%"

:: ── Skip if nothing to process ─────────────────────────────
if %EMAIL_COUNT% equ 0 (
    echo [INFO] No pending email tasks found. Skipping Claude invocation. >> "%LOG_FILE%"
    echo [INFO] No pending email tasks — skipping.
    echo  Result  : SKIPPED (nothing to process) >> "%LOG_FILE%"
    echo  Finished: %DATE% %TIME% >> "%LOG_FILE%"
    echo ============================================================ >> "%LOG_FILE%"
    exit /b 0
)

:: ── Run Claude command ─────────────────────────────────────
echo [INFO] Processing %EMAIL_COUNT% email task(s)...
echo [INFO] Processing %EMAIL_COUNT% email task(s)... >> "%LOG_FILE%"

claude "Process all pending email tasks in Needs_Action using FILE_PROCESSOR_SKILL" >> "%LOG_FILE%" 2>&1
set CLAUDE_EXIT=%ERRORLEVEL%

:: ── Result handling ────────────────────────────────────────
echo. >> "%LOG_FILE%"
echo ============================================================ >> "%LOG_FILE%"
if %CLAUDE_EXIT% equ 0 (
    echo  Result  : SUCCESS >> "%LOG_FILE%"
    echo [SUCCESS] Email processing completed. See %LOG_FILE%
) else (
    echo  Result  : FAILED (exit code %CLAUDE_EXIT%) >> "%LOG_FILE%"
    echo [ERROR] Email processing failed with exit code %CLAUDE_EXIT%. See %LOG_FILE%
)
echo  Finished: %DATE% %TIME% >> "%LOG_FILE%"
echo ============================================================ >> "%LOG_FILE%"

:: ── Rotate old logs (keep last 14 days — runs more often) ──
forfiles /p "%LOG_DIR%" /m "%TASK_NAME%_*.log" /d -14 /c "cmd /c del @path" 2>nul

exit /b %CLAUDE_EXIT%
