# Windows Task Scheduler Setup Guide
## AI Employee Vault — Gold Tier Automation

**Version:** 1.0 | **OS:** Windows 10 / 11 | **Created:** 2026-02-24

---

## Overview

This guide registers four AI Employee automation tasks with Windows Task Scheduler so every component starts and runs without manual intervention.

| # | Task | Script | Schedule | Type |
|---|------|--------|----------|------|
| 1 | Ralph Wiggum Loop | `ralph_wiggum_loop.py` | At system startup | Continuous / background |
| 2 | Gmail Watcher | `gmail_watcher.py` | At system startup | Continuous / background |
| 3 | Weekly CEO Briefing | `weekly_ceo_briefing.py` | Every Sunday 8:00 AM | One-shot / weekly |
| 4 | LinkedIn Auto-Poster | `linkedin_auto_poster.py` | Mon, Wed, Fri 10:00 AM | One-shot / 3×/week |

> **Tasks 1 & 2** run forever in the background (like services).
> **Tasks 3 & 4** launch, do their job, and exit.

---

## Prerequisites

Before registering any task, confirm the following:

### 1. Locate your Python executable

Open **Command Prompt** (Win+R → `cmd` → Enter) and run:

```
where python
```

Expected output (may vary):

```
C:\Users\Esha Khan\AppData\Local\Programs\Python\Python314\python.exe
```

Also note `pythonw.exe` in the same folder — this variant runs without a console window
(ideal for background tasks 1 and 2).

```
C:\Users\Esha Khan\AppData\Local\Programs\Python\Python314\pythonw.exe
```

Write these paths down — you will enter them in every task's Action.

### 2. Confirm the vault path

```
D:\coding\Hackaton\hac_0\AI_Employee_Vault
```

Every task uses this as its **Start In** (working directory).

### 3. Create the Logs directory

```cmd
mkdir "D:\coding\Hackaton\hac_0\AI_Employee_Vault\Logs"
```

All task output is redirected to log files here.

### 4. Create wrapper .bat scripts

Wrapper scripts solve three problems at once: they set the working directory, redirect
`stdout`/`stderr` to dated log files, and let Task Scheduler call a single `.bat` rather
than juggling long argument strings.

Create each file below exactly as shown (use Notepad or any text editor).

---

#### `run_ralph.bat`

**Full path:** `D:\coding\Hackaton\hac_0\AI_Employee_Vault\run_ralph.bat`

```batch
@echo off
REM AI Employee — Ralph Wiggum Autonomous Loop
REM Launched by Windows Task Scheduler at startup

cd /d "D:\coding\Hackaton\hac_0\AI_Employee_Vault"

set LOGFILE=Logs\ralph_%DATE:~10,4%-%DATE:~4,2%-%DATE:~7,2%.log

echo [%DATE% %TIME%] Ralph starting... >> "%LOGFILE%"
"C:\Users\Esha Khan\AppData\Local\Programs\Python\Python314\python.exe" ^
    ralph_wiggum_loop.py >> "%LOGFILE%" 2>&1

echo [%DATE% %TIME%] Ralph exited (code %ERRORLEVEL%) >> "%LOGFILE%"
```

---

#### `run_gmail_watcher.bat`

**Full path:** `D:\coding\Hackaton\hac_0\AI_Employee_Vault\run_gmail_watcher.bat`

```batch
@echo off
REM AI Employee — Gmail Inbox Watcher
REM Launched by Windows Task Scheduler at startup

cd /d "D:\coding\Hackaton\hac_0\AI_Employee_Vault"

set LOGFILE=Logs\gmail_watcher_%DATE:~10,4%-%DATE:~4,2%-%DATE:~7,2%.log

echo [%DATE% %TIME%] Gmail Watcher starting... >> "%LOGFILE%"
"C:\Users\Esha Khan\AppData\Local\Programs\Python\Python314\python.exe" ^
    gmail_watcher.py >> "%LOGFILE%" 2>&1

echo [%DATE% %TIME%] Gmail Watcher exited (code %ERRORLEVEL%) >> "%LOGFILE%"
```

---

#### `run_ceo_briefing.bat`

**Full path:** `D:\coding\Hackaton\hac_0\AI_Employee_Vault\run_ceo_briefing.bat`

```batch
@echo off
REM AI Employee — Weekly CEO Briefing Generator
REM Launched by Windows Task Scheduler every Sunday at 08:00

cd /d "D:\coding\Hackaton\hac_0\AI_Employee_Vault"

set LOGFILE=Logs\ceo_briefing_%DATE:~10,4%-%DATE:~4,2%-%DATE:~7,2%.log

echo [%DATE% %TIME%] CEO Briefing starting... >> "%LOGFILE%"
"C:\Users\Esha Khan\AppData\Local\Programs\Python\Python314\python.exe" ^
    weekly_ceo_briefing.py >> "%LOGFILE%" 2>&1

echo [%DATE% %TIME%] CEO Briefing completed (code %ERRORLEVEL%) >> "%LOGFILE%"
```

---

#### `run_linkedin_poster.bat`

**Full path:** `D:\coding\Hackaton\hac_0\AI_Employee_Vault\run_linkedin_poster.bat`

```batch
@echo off
REM AI Employee — LinkedIn Auto-Poster (M/W/F smart check)
REM Launched by Windows Task Scheduler Mon/Wed/Fri at 10:00

cd /d "D:\coding\Hackaton\hac_0\AI_Employee_Vault"

set LOGFILE=Logs\linkedin_%DATE:~10,4%-%DATE:~4,2%-%DATE:~7,2%.log

echo [%DATE% %TIME%] LinkedIn Auto-Poster check starting... >> "%LOGFILE%"
"C:\Users\Esha Khan\AppData\Local\Programs\Python\Python314\python.exe" ^
    linkedin_auto_poster.py --ralph-check >> "%LOGFILE%" 2>&1

echo [%DATE% %TIME%] LinkedIn check completed (code %ERRORLEVEL%) >> "%LOGFILE%"
```

---

## Opening Task Scheduler

**Method A — Start Menu**

```
Win key  →  type "Task Scheduler"  →  Enter
```

**Method B — Run dialog**

```
Win + R  →  taskschd.msc  →  Enter
```

**Method C — Command line**

```cmd
taskschd.msc
```

The Task Scheduler window looks like this:

```
┌─────────────────────────────────────────────────────────────────────┐
│  Task Scheduler                                              [─][□][×]│
├──────────────────┬──────────────────────────────┬───────────────────┤
│ Task Scheduler   │  Task Scheduler (Local)       │  Actions          │
│ Library          │                               │ ─────────────────│
│ ├─ Microsoft     │  Overview                     │ Create Basic Task │
│ │  └─ Windows    │  ─────────────────────────    │ Create Task...    │
│ └─ (your tasks   │  To begin, select a node      │ Import Task...    │
│    appear here)  │  in the left pane.            │ Display All...    │
│                  │                               │ View             ▶│
│                  │                               │ Refresh           │
│                  │                               │ Help              │
└──────────────────┴──────────────────────────────┴───────────────────┘
```

Click **"Create Task..."** in the right-hand Actions panel for each task below.
(Do not use "Create Basic Task" — it doesn't expose all the settings we need.)

---

## Task 1: Ralph Wiggum Loop

**What it does:** The autonomous OODA reasoning loop. Observes vault state, decides on actions, executes via Claude Code. Runs every 60 minutes, respects quiet hours (23:00–06:00), pauses after 3 consecutive errors.

**When:** At every system startup, restarted automatically if it crashes.

---

### Step 1 — General Tab

Click **Create Task...**. The General tab opens first.

```
┌─────────────────────── Create Task ──────────────────────────────┐
│  General  │  Triggers  │  Actions  │  Conditions  │  Settings    │
├──────────────────────────────────────────────────────────────────┤
│                                                                    │
│  Name:        [ AIEmployee-Ralph                              ]    │
│                                                                    │
│  Description: [ AI Employee Ralph Wiggum autonomous loop.     ]   │
│               [ Observes vault, decides actions, executes via ]   │
│               [ Claude Code. Runs every 60 min.               ]   │
│                                                                    │
│  Security options:                                                 │
│  ○ Run only when user is logged on                                 │
│  ● Run whether user is logged on or not          ← SELECT THIS    │
│    □ Do not store password                                         │
│                                                                    │
│  ☑ Run with highest privileges                   ← CHECK THIS     │
│                                                                    │
│  Configure for: [ Windows 10               ▼ ]                    │
│                                                                    │
│                                              [ OK ]  [ Cancel ]   │
└──────────────────────────────────────────────────────────────────┘
```

**Fill in exactly:**

| Field | Value |
|-------|-------|
| Name | `AIEmployee-Ralph` |
| Description | `AI Employee Ralph Wiggum autonomous reasoning loop. OODA cycle every 60 min.` |
| Security | **Run whether user is logged on or not** |
| Run with highest privileges | ☑ checked |
| Configure for | Windows 10 (or Windows 11) |

> When you select "Run whether user is logged on or not" and click OK at the end,
> Windows will prompt for your account password. This lets the task run even when
> you are not at the keyboard.

---

### Step 2 — Triggers Tab

Click the **Triggers** tab → click **New...**

```
┌──────────────────── New Trigger ─────────────────────────────────┐
│                                                                    │
│  Begin the task:  [ At startup                      ▼ ]           │
│                                                                    │
│  ─── Advanced settings ───────────────────────────────────────    │
│                                                                    │
│  □ Delay task for:  [ 30 seconds        ▼ ]  ← SET TO 30 sec      │
│                                                                    │
│  □ Repeat task every:  [           ] for a duration of: [      ]  │
│  (Leave blank — Ralph manages its own loop internally)             │
│                                                                    │
│  □ Stop task if it runs longer than:  [                  ]        │
│  (Leave blank — Ralph runs indefinitely)                           │
│                                                                    │
│  □ Expire:  [                                    ]                 │
│                                                                    │
│  ☑ Enabled                                       ← MUST be checked│
│                                                                    │
│                                              [ OK ]  [ Cancel ]   │
└──────────────────────────────────────────────────────────────────┘
```

**Settings:**

| Field | Value |
|-------|-------|
| Begin the task | **At startup** |
| Delay task for | ☑ checked, **30 seconds** (lets the system fully boot first) |
| Repeat task every | Leave unchecked (Ralph loops internally) |
| Stop task if runs longer than | Leave unchecked |
| Enabled | ☑ checked |

Click **OK**.

---

### Step 3 — Actions Tab

Click the **Actions** tab → click **New...**

```
┌──────────────────── New Action ──────────────────────────────────┐
│                                                                    │
│  Action:  [ Start a program          ▼ ]                          │
│                                                                    │
│  Settings:                                                         │
│                                                                    │
│  Program/script:                                                   │
│  [ D:\coding\Hackaton\hac_0\AI_Employee_Vault\run_ralph.bat  ]    │
│                                                            [Browse]│
│                                                                    │
│  Add arguments (optional):                                         │
│  [                                                           ]     │
│  (leave blank — arguments are inside the .bat file)               │
│                                                                    │
│  Start in (optional):                                              │
│  [ D:\coding\Hackaton\hac_0\AI_Employee_Vault                ]    │
│                                                                    │
│                                              [ OK ]  [ Cancel ]   │
└──────────────────────────────────────────────────────────────────┘
```

| Field | Value |
|-------|-------|
| Action | Start a program |
| Program/script | `D:\coding\Hackaton\hac_0\AI_Employee_Vault\run_ralph.bat` |
| Add arguments | *(leave empty)* |
| Start in | `D:\coding\Hackaton\hac_0\AI_Employee_Vault` |

Click **OK**.

---

### Step 4 — Conditions Tab

```
┌──────────────────── Conditions ──────────────────────────────────┐
│  Idle                                                              │
│  □ Start the task only if the computer is idle for:  [        ]   │
│                                                                    │
│  Power                                                             │
│  □ Start the task only if the computer is on AC power             │
│  ☑ Stop if the computer switches to battery power  ← UNCHECK THIS │
│  □ Wake the computer to run this task                              │
│                                                                    │
│  Network                                                           │
│  □ Start only if the following network connection is available:    │
│    [ Any connection                               ▼ ]             │
│                                                                    │
└──────────────────────────────────────────────────────────────────┘
```

| Setting | Value |
|---------|-------|
| Start only if computer is idle | ☐ unchecked |
| Start only if on AC power | ☐ unchecked |
| Stop if switches to battery | ☐ **unchecked** (important — Ralph must keep running on laptop) |
| Wake computer to run | ☐ unchecked |
| Network | ☐ unchecked |

---

### Step 5 — Settings Tab

```
┌──────────────────── Settings ────────────────────────────────────┐
│  ☑ Allow task to be run on demand                                  │
│  □ Run task as soon as possible after a scheduled start is missed  │
│  □ If the task fails, restart every:  [ 1 minute    ▼ ]          │
│    Attempt to restart up to:           [ 3          ] times        │
│  □ Stop the task if it runs longer than:  [                ]      │
│  □ If the running task does not end when requested, force it...    │
│  ☑ If the task is not scheduled to run again, delete it after: ☐  │
│                                                                    │
│  If the task is already running, then the following rule applies:  │
│  [ Do not start a new instance              ▼ ]  ← SELECT THIS    │
│                                                                    │
└──────────────────────────────────────────────────────────────────┘
```

| Setting | Value |
|---------|-------|
| Allow task to be run on demand | ☑ checked |
| If task fails, restart every | ☑ checked, **1 minute**, up to **3 times** |
| Stop if runs longer than | ☐ unchecked |
| If already running | **Do not start a new instance** |

Click **OK**. Enter your Windows password when prompted.

---

## Task 2: Gmail Watcher

**What it does:** Polls Gmail every 5 minutes for new unread emails. Converts each email into a structured `.md` file in `Needs_Action/` for Ralph to process.

**When:** At system startup, alongside Ralph.

---

### Step 1 — General Tab

```
┌──────────── General ─────────────────────────────────────────────┐
│  Name:        [ AIEmployee-GmailWatcher                      ]    │
│  Description: [ Polls Gmail inbox every 5 min, creates task   ]   │
│               [ files in Needs_Action/ for Ralph to process.  ]   │
│                                                                    │
│  ● Run whether user is logged on or not       ← SELECT THIS       │
│  ☑ Run with highest privileges                ← CHECK THIS        │
│  Configure for: [ Windows 10               ▼ ]                    │
└──────────────────────────────────────────────────────────────────┘
```

| Field | Value |
|-------|-------|
| Name | `AIEmployee-GmailWatcher` |
| Description | `Polls Gmail inbox every 5 min. Creates Needs_Action/ task files.` |
| Security | Run whether user is logged on or not |
| Run with highest privileges | ☑ checked |

---

### Step 2 — Triggers Tab → New

| Field | Value |
|-------|-------|
| Begin the task | **At startup** |
| Delay task for | ☑ checked, **1 minute** (start after Ralph is up) |
| Repeat task every | ☐ unchecked (script loops internally) |
| Enabled | ☑ checked |

> The Gmail Watcher script has its own internal `POLL_INTERVAL = 300` (5 minutes) loop.
> Task Scheduler just needs to launch it once at boot.

---

### Step 3 — Actions Tab → New

| Field | Value |
|-------|-------|
| Program/script | `D:\coding\Hackaton\hac_0\AI_Employee_Vault\run_gmail_watcher.bat` |
| Add arguments | *(leave empty)* |
| Start in | `D:\coding\Hackaton\hac_0\AI_Employee_Vault` |

---

### Step 4 — Conditions Tab

| Setting | Value |
|---------|-------|
| Start only if on AC power | ☐ unchecked |
| Stop if switches to battery | ☐ unchecked |
| Network connection available | ☑ checked, **Any connection** (Gmail needs the internet) |

```
  Network
  ☑ Start only if the following network connection is available:
    [ Any connection                               ▼ ]
```

---

### Step 5 — Settings Tab

| Setting | Value |
|---------|-------|
| Allow on demand | ☑ checked |
| If task fails, restart | ☑ **1 minute**, **3 times** |
| If already running | **Do not start a new instance** |

---

## Task 3: Weekly CEO Briefing

**What it does:** Generates a 5-section business audit report (`Reports/CEO_Briefing_YYYY-MM-DD.md`) covering the past 7 days of AI Employee activity. Runs once, exits cleanly.

**When:** Every Sunday at 08:00 AM.

---

### Step 1 — General Tab

```
┌──────────── General ─────────────────────────────────────────────┐
│  Name:        [ AIEmployee-CEOBriefing                       ]    │
│  Description: [ Generates weekly CEO briefing report every    ]   │
│               [ Sunday at 08:00. Output: Reports/ directory.  ]   │
│                                                                    │
│  ● Run whether user is logged on or not       ← SELECT THIS       │
│  ☑ Run with highest privileges                ← CHECK THIS        │
│  Configure for: [ Windows 10               ▼ ]                    │
└──────────────────────────────────────────────────────────────────┘
```

| Field | Value |
|-------|-------|
| Name | `AIEmployee-CEOBriefing` |
| Description | `Weekly CEO briefing generator. Runs every Sunday 08:00. Output: Reports/` |
| Security | Run whether user is logged on or not |
| Run with highest privileges | ☑ checked |

---

### Step 2 — Triggers Tab → New

```
┌──────────────────── New Trigger ─────────────────────────────────┐
│                                                                    │
│  Begin the task:  [ On a schedule                   ▼ ]           │
│                                                                    │
│  Settings:                                                         │
│  ○ One time                                                        │
│  ○ Daily                                                           │
│  ● Weekly                             ← SELECT THIS               │
│    Recur every:  [ 1 ] weeks on:                                   │
│    □ Mon  □ Tue  □ Wed  □ Thu  □ Fri  □ Sat  ☑ Sun               │
│                                            ↑ CHECK SUNDAY ONLY    │
│                                                                    │
│  Start:  [ 2026-02-01 ]  [ 08:00:00  ]  □ Synchronize...         │
│                            ↑ 8:00 AM                              │
│                                                                    │
│  Advanced settings:                                                │
│  □ Delay task for:  [                  ]                           │
│  □ Repeat task every:  [              ]                            │
│  □ Stop task if it runs longer than:  [ 1 hour         ]          │
│  ☑ Enabled                                                        │
│                                                                    │
│                                              [ OK ]  [ Cancel ]   │
└──────────────────────────────────────────────────────────────────┘
```

| Field | Value |
|-------|-------|
| Begin the task | **On a schedule** |
| Settings | **Weekly** |
| Recur every | **1** week(s) |
| Days | ☑ **Sunday** only |
| Start time | **08:00:00** |
| Stop task if runs longer than | ☑ checked, **1 hour** (safety cap) |
| Enabled | ☑ checked |

---

### Step 3 — Actions Tab → New

| Field | Value |
|-------|-------|
| Program/script | `D:\coding\Hackaton\hac_0\AI_Employee_Vault\run_ceo_briefing.bat` |
| Add arguments | *(leave empty)* |
| Start in | `D:\coding\Hackaton\hac_0\AI_Employee_Vault` |

---

### Step 4 — Conditions Tab

| Setting | Value |
|---------|-------|
| Start only if on AC power | ☐ unchecked |
| Stop if switches to battery | ☐ unchecked |
| Network | ☐ unchecked (reads local files only) |

---

### Step 5 — Settings Tab

| Setting | Value |
|---------|-------|
| Run task as soon as possible after scheduled start is missed | ☑ checked |
| If task fails, restart | ☑ **5 minutes**, **2 times** |
| Stop if runs longer than | ☑ **1 hour** |
| If already running | **Do not start a new instance** |

> **"Run as soon as possible after missed start"** is important here — if the computer
> was off Sunday morning, it will generate the briefing the next time it boots.

---

## Task 4: LinkedIn Auto-Poster

**What it does:** Checks whether a LinkedIn post should be generated or an approved post should be executed. Smart mode (`--ralph-check`) is idempotent — safe to run even outside the posting window. Runs three times per week, exits cleanly.

**When:** Every Monday, Wednesday, Friday at 10:00 AM.

---

### Step 1 — General Tab

| Field | Value |
|-------|-------|
| Name | `AIEmployee-LinkedInPoster` |
| Description | `LinkedIn content auto-poster. M/W/F 10:00. SIMULATION MODE by default. HITL approval required.` |
| Security | Run whether user is logged on or not |
| Run with highest privileges | ☑ checked |

---

### Step 2 — Triggers Tab → New

```
┌──────────────────── New Trigger ─────────────────────────────────┐
│  Begin the task:  [ On a schedule               ▼ ]              │
│                                                                    │
│  ● Weekly                                                          │
│    Recur every:  [ 1 ] weeks on:                                   │
│    ☑ Mon  □ Tue  ☑ Wed  □ Thu  □ Fri  □ Sat  □ Sun              │
│                                                                    │
│  Wait — Task Scheduler weekly triggers select one day-set.        │
│  Create TWO triggers if Mon+Wed+Fri doesn't appear as one option: │
│                                                                    │
│  Trigger 1: Weekly, ☑ Mon ☑ Wed ☑ Fri, 10:00:00 AM               │
│  (Most versions of Windows support multi-day weekly triggers)      │
│                                                                    │
│  Start:  [ 2026-02-01 ]  [ 10:00:00 ]                            │
│                                                                    │
│  ☑ Enabled                                                        │
└──────────────────────────────────────────────────────────────────┘
```

| Field | Value |
|-------|-------|
| Begin the task | **On a schedule** → **Weekly** |
| Recur every | **1** week(s) |
| Days | ☑ **Mon** ☑ **Wed** ☑ **Fri** |
| Start time | **10:00:00** |
| Enabled | ☑ checked |

> If your Windows version does not allow selecting multiple days in one trigger, create
> three separate triggers (one per day) all set to 10:00 AM weekly.

---

### Step 3 — Actions Tab → New

| Field | Value |
|-------|-------|
| Program/script | `D:\coding\Hackaton\hac_0\AI_Employee_Vault\run_linkedin_poster.bat` |
| Add arguments | *(leave empty)* |
| Start in | `D:\coding\Hackaton\hac_0\AI_Employee_Vault` |

---

### Step 4 — Conditions Tab

| Setting | Value |
|---------|-------|
| Start only if on AC power | ☐ unchecked |
| Network connection available | ☑ **Any connection** (needed for LinkedIn API in live mode) |

---

### Step 5 — Settings Tab

| Setting | Value |
|---------|-------|
| Run task as soon as possible after missed start | ☑ checked |
| If task fails, restart | ☑ **5 minutes**, **2 times** |
| Stop if runs longer than | ☑ **30 minutes** |
| If already running | **Do not start a new instance** |

---

## PowerShell Alternative (Advanced)

If you prefer scripting over the GUI, run the following in an **Administrator PowerShell** window.
This registers all four tasks in one shot.

```powershell
# ── CONFIGURATION ────────────────────────────────────────────────────
$vault   = "D:\coding\Hackaton\hac_0\AI_Employee_Vault"
$python  = "C:\Users\Esha Khan\AppData\Local\Programs\Python\Python314\python.exe"
$user    = $env:USERNAME          # current Windows user
# ─────────────────────────────────────────────────────────────────────

# Helper: common settings object
function Get-Settings($stopMins=0, $restartMins=1, $restartCount=3) {
    $s = New-ScheduledTaskSettingsSet `
        -MultipleInstances IgnoreNew `
        -ExecutionTimeLimit (?: $stopMins { [TimeSpan]::FromMinutes($stopMins) } { [TimeSpan]::Zero }) `
        -RestartCount $restartCount `
        -RestartInterval ([TimeSpan]::FromMinutes($restartMins))
    $s.AllowDemandStart = $true
    return $s
}

# ── Task 1: Ralph ────────────────────────────────────────────────────
$a1 = New-ScheduledTaskAction `
    -Execute "$vault\run_ralph.bat" `
    -WorkingDirectory $vault
$t1 = New-ScheduledTaskTrigger -AtStartup
$t1.Delay = "PT30S"   # 30 second delay
Register-ScheduledTask `
    -TaskName    "AIEmployee-Ralph" `
    -Description "AI Employee Ralph Wiggum autonomous reasoning loop" `
    -Action      $a1 `
    -Trigger     $t1 `
    -Settings    (Get-Settings -restartMins 1 -restartCount 3) `
    -RunLevel    Highest `
    -Force
Write-Host "Task 1 registered: AIEmployee-Ralph"

# ── Task 2: Gmail Watcher ────────────────────────────────────────────
$a2 = New-ScheduledTaskAction `
    -Execute "$vault\run_gmail_watcher.bat" `
    -WorkingDirectory $vault
$t2 = New-ScheduledTaskTrigger -AtStartup
$t2.Delay = "PT1M"   # 1 minute delay — start after Ralph
Register-ScheduledTask `
    -TaskName    "AIEmployee-GmailWatcher" `
    -Description "Gmail inbox watcher. Polls every 5 min. Creates Needs_Action/ files." `
    -Action      $a2 `
    -Trigger     $t2 `
    -Settings    (Get-Settings -restartMins 1 -restartCount 3) `
    -RunLevel    Highest `
    -Force
Write-Host "Task 2 registered: AIEmployee-GmailWatcher"

# ── Task 3: CEO Briefing ─────────────────────────────────────────────
$a3 = New-ScheduledTaskAction `
    -Execute "$vault\run_ceo_briefing.bat" `
    -WorkingDirectory $vault
$t3 = New-ScheduledTaskTrigger -Weekly -WeeksInterval 1 -DaysOfWeek Sunday -At "08:00"
$s3 = New-ScheduledTaskSettingsSet `
    -MultipleInstances IgnoreNew `
    -ExecutionTimeLimit ([TimeSpan]::FromHours(1)) `
    -StartWhenAvailable `
    -RestartCount 2 `
    -RestartInterval ([TimeSpan]::FromMinutes(5))
Register-ScheduledTask `
    -TaskName    "AIEmployee-CEOBriefing" `
    -Description "Weekly CEO briefing generator. Every Sunday 08:00." `
    -Action      $a3 `
    -Trigger     $t3 `
    -Settings    $s3 `
    -RunLevel    Highest `
    -Force
Write-Host "Task 3 registered: AIEmployee-CEOBriefing"

# ── Task 4: LinkedIn Auto-Poster ─────────────────────────────────────
$a4 = New-ScheduledTaskAction `
    -Execute "$vault\run_linkedin_poster.bat" `
    -WorkingDirectory $vault
# Mon + Wed + Fri at 10:00
$t4 = New-ScheduledTaskTrigger -Weekly -WeeksInterval 1 `
    -DaysOfWeek Monday,Wednesday,Friday -At "10:00"
$s4 = New-ScheduledTaskSettingsSet `
    -MultipleInstances IgnoreNew `
    -ExecutionTimeLimit ([TimeSpan]::FromMinutes(30)) `
    -StartWhenAvailable `
    -RestartCount 2 `
    -RestartInterval ([TimeSpan]::FromMinutes(5))
Register-ScheduledTask `
    -TaskName    "AIEmployee-LinkedInPoster" `
    -Description "LinkedIn auto-poster. Mon/Wed/Fri 10:00. HITL approval required." `
    -Action      $a4 `
    -Trigger     $t4 `
    -Settings    $s4 `
    -RunLevel    Highest `
    -Force
Write-Host "Task 4 registered: AIEmployee-LinkedInPoster"

Write-Host "`nAll 4 tasks registered. Verify with: Get-ScheduledTask -TaskName 'AIEmployee-*'"
```

---

## Verification

### Check task registration

Open **Task Scheduler** and look in **Task Scheduler Library** for four entries:

```
AIEmployee-CEOBriefing
AIEmployee-GmailWatcher
AIEmployee-LinkedInPoster
AIEmployee-Ralph
```

Or in PowerShell:

```powershell
Get-ScheduledTask -TaskName "AIEmployee-*" | Select-Object TaskName, State, LastRunTime, NextRunTime
```

Expected output:

```
TaskName                    State    LastRunTime         NextRunTime
--------                    -----    -----------         -----------
AIEmployee-CEOBriefing      Ready    N/A                 2026-03-01 08:00
AIEmployee-GmailWatcher     Running  2026-02-24 09:01    N/A
AIEmployee-LinkedInPoster   Ready    N/A                 2026-02-25 10:00
AIEmployee-Ralph            Running  2026-02-24 09:00    N/A
```

### Run a task manually (on-demand test)

In Task Scheduler: right-click a task → **Run**

Or in PowerShell:

```powershell
Start-ScheduledTask -TaskName "AIEmployee-CEOBriefing"
```

### Check task exit codes

```powershell
(Get-ScheduledTaskInfo -TaskName "AIEmployee-Ralph").LastTaskResult
```

`0` = success. Any non-zero value = error — check the log file.

### Watch a log file live (PowerShell)

```powershell
$log = "D:\coding\Hackaton\hac_0\AI_Employee_Vault\Logs\ralph_2026-02-24.log"
Get-Content $log -Wait -Tail 20
```

### Confirm Ralph is actually running

```powershell
Get-Process python | Select-Object Id, CPU, WorkingSet, StartTime
```

---

## Troubleshooting

### Task shows "Ready" but never runs at startup

**Cause:** "Run whether user is logged on or not" requires your Windows password to be stored.

**Fix:**
1. Double-click the task → General tab
2. Click **Change User or Group** and confirm your account
3. Click **OK** — Windows prompts for your password
4. Enter it and click **OK**

If you use a Microsoft account (not local account), use your full Microsoft account password or switch to a local account for the task.

---

### Task shows state "Disabled"

**Fix:** Right-click task → **Enable**

---

### Error code `0x1` (general failure)

The script ran but exited with a non-zero code.

**Fix:**
1. Open the task's log file in `Logs/`
2. Read the last 20 lines for the Python traceback
3. Common causes:
   - Missing dependency: `pip install -r requirements.txt`
   - Missing `credentials.json` (Gmail/LinkedIn)
   - `token.json` expired — re-run the OAuth flow

---

### Error code `0x8007010B` — Directory not found

**Cause:** The "Start In" path doesn't exist or has a typo.

**Fix:**
1. Open the task → Actions tab → Edit
2. Verify **Start in** = `D:\coding\Hackaton\hac_0\AI_Employee_Vault` (no trailing backslash)
3. Confirm the directory exists in File Explorer

---

### Error code `0x41306` — Task is terminated

**Cause:** The task hit the "Stop task if it runs longer than" limit.

**Fix:** For Ralph and Gmail Watcher, ensure this limit is **unchecked** (they run indefinitely).

---

### Gmail Watcher exits immediately

**Cause:** `token.json` is missing or expired.

**Fix:**
```cmd
cd D:\coding\Hackaton\hac_0\AI_Employee_Vault
python gmail_watcher.py
```
Run it manually once — it will open a browser for OAuth consent and save `token.json`. After that, the scheduled task will work.

---

### Ralph exits immediately

**Cause:** Claude CLI not found.

**Fix:**
```cmd
where claude
```
If not found, install Claude Code:
```cmd
npm install -g @anthropic-ai/claude-code
```
Then re-run Ralph manually once to confirm it starts:
```cmd
python ralph_wiggum_loop.py --once
```

---

### LinkedIn task runs but no post is generated

**Cause:** Today is not Monday/Wednesday/Friday, or it's outside the 10 AM ±90 minute window.

**This is correct behaviour.** The `--ralph-check` flag is idempotent — it exits cleanly with no action if conditions aren't met.

To force a post regardless of schedule:
```cmd
python linkedin_auto_poster.py --generate
```

---

### Task runs but log file is empty

**Cause:** Python output is not being flushed to the file.

**Fix:** Add `-u` flag for unbuffered output in the `.bat` file:

```batch
python -u ralph_wiggum_loop.py >> "%LOGFILE%" 2>&1
```

---

### Multiple python.exe processes (zombie instances)

**Cause:** Task Scheduler launched a second instance before the first exited.

**Fix:** All tasks are configured with **"Do not start a new instance"** — verify this setting
is in place:

1. Open task → Settings tab
2. "If the task is already running, then the following rule applies:"
3. Must be set to **Do not start a new instance**

---

## Task Management Reference

### View all AI Employee tasks

```powershell
Get-ScheduledTask -TaskName "AIEmployee-*" | Format-Table TaskName, State -AutoSize
```

### Disable a task temporarily

```powershell
Disable-ScheduledTask -TaskName "AIEmployee-GmailWatcher"
```

### Re-enable a task

```powershell
Enable-ScheduledTask -TaskName "AIEmployee-GmailWatcher"
```

### Stop a running task

```powershell
Stop-ScheduledTask -TaskName "AIEmployee-Ralph"
```

### Remove a task entirely

```powershell
Unregister-ScheduledTask -TaskName "AIEmployee-Ralph" -Confirm:$false
```

### Export a task definition to XML (backup)

```powershell
Export-ScheduledTask -TaskName "AIEmployee-Ralph" | Out-File ralph_task_backup.xml
```

### Import a task from XML backup

```powershell
Register-ScheduledTask -Xml (Get-Content ralph_task_backup.xml -Raw) -TaskName "AIEmployee-Ralph"
```

### View task history in Event Viewer

1. Open **Event Viewer** (`eventvwr.msc`)
2. Navigate to: `Applications and Services Logs → Microsoft → Windows → TaskScheduler → Operational`
3. Filter by Task Category: **AIEmployee-Ralph** (or any task name)

Each task run creates events:
- **Event ID 100** — Task started
- **Event ID 102** — Task completed successfully
- **Event ID 101** — Task failed to start
- **Event ID 103** — Task stopped (user or system)

---

## Quick Start Checklist

Run through this list after creating all four tasks:

```
□ 1. run_ralph.bat          created in vault root
□ 2. run_gmail_watcher.bat  created in vault root
□ 3. run_ceo_briefing.bat   created in vault root
□ 4. run_linkedin_poster.bat created in vault root
□ 5. AIEmployee-Ralph        registered, State = Running
□ 6. AIEmployee-GmailWatcher registered, State = Running
□ 7. AIEmployee-CEOBriefing  registered, State = Ready (runs Sunday)
□ 8. AIEmployee-LinkedInPoster registered, State = Ready (runs M/W/F)
□ 9. Logs/ directory exists
□ 10. Log files are being written (check after 5 min)
□ 11. ralph_state.json appears in Logs/ralph/ after first cycle
□ 12. CEO briefing: tested with Start-ScheduledTask, report in Reports/
□ 13. LinkedIn poster: tested with --status, next slot shown correctly
□ 14. Restart machine → verify Ralph + Gmail auto-start within 90 sec
```

---

## Summary

| Task Name | Trigger | Script | Log |
|-----------|---------|--------|-----|
| `AIEmployee-Ralph` | At startup (+30s) | `ralph_wiggum_loop.py` | `Logs/ralph_YYYY-MM-DD.log` |
| `AIEmployee-GmailWatcher` | At startup (+1m) | `gmail_watcher.py` | `Logs/gmail_watcher_YYYY-MM-DD.log` |
| `AIEmployee-CEOBriefing` | Weekly, Sun 08:00 | `weekly_ceo_briefing.py` | `Logs/ceo_briefing_YYYY-MM-DD.log` |
| `AIEmployee-LinkedInPoster` | Weekly, M/W/F 10:00 | `linkedin_auto_poster.py` | `Logs/linkedin_YYYY-MM-DD.log` |

---

*AI Employee Vault — Gold v1.0*
*Guide version 1.0 — 2026-02-24*
