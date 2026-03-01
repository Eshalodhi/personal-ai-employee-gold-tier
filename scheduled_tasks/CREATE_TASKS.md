# Windows Task Scheduler Setup Guide
## AI Employee Vault — Silver Tier Automation

This guide walks you through creating the three scheduled tasks that automate
the AI Employee's daily workflow. Each task runs a `.bat` file that invokes
`claude` with a specific prompt, then logs the output to `scheduled_tasks/logs/`.

---

## Prerequisites

Before creating the tasks, verify these are in place:

- [ ] `claude` CLI is installed and on your `PATH`
  - Test: open Command Prompt and run `claude --version`
- [ ] Vault directory exists: `D:\coding\hackaton\hac_0\AI_Employee_Vault`
- [ ] All three `.bat` files are present in `scheduled_tasks\`
- [ ] `scheduled_tasks\logs\` folder exists (or will be auto-created on first run)

---

## Opening Windows Task Scheduler

1. Press **Win + R**, type `taskschd.msc`, press **Enter**
   — or —
   Search for **"Task Scheduler"** in the Start menu

2. In the left panel, click **"Task Scheduler Library"** to see all existing tasks

3. All three AI Employee tasks will live here at the top level (or create a
   subfolder: right-click Library → **New Folder** → name it `AI Employee`)

---

## Task 1 — Morning Briefing (8:00 AM Daily)

### Step 1 — Open the Create Task dialog
- In the right-hand **Actions** panel, click **"Create Task..."**
  *(not "Create Basic Task" — we need more control)*

### Step 2 — General tab
| Field | Value |
|-------|-------|
| Name | `AI Employee — Morning Briefing` |
| Description | `Generates morning briefing with pending tasks and recent emails` |
| Run whether user is logged on or not | Selected |
| Run with highest privileges | Checked |
| Configure for | Windows 10 / Windows 11 |

### Step 3 — Triggers tab
1. Click **"New..."**
2. Set the following:

| Field | Value |
|-------|-------|
| Begin the task | On a schedule |
| Settings | Daily |
| Start | Today's date, **8:00:00 AM** |
| Recur every | 1 day |
| Enabled | Checked |

3. Click **OK**

### Step 4 — Actions tab
1. Click **"New..."**
2. Set the following:

| Field | Value |
|-------|-------|
| Action | Start a program |
| Program/script | `D:\coding\hackaton\hac_0\AI_Employee_Vault\scheduled_tasks\morning_briefing.bat` |
| Add arguments | *(leave blank)* |
| Start in | `D:\coding\hackaton\hac_0\AI_Employee_Vault` |

3. Click **OK**

### Step 5 — Conditions tab
| Field | Value |
|-------|-------|
| Start only if the computer is on AC power | Uncheck (so it runs on battery too) |

### Step 6 — Settings tab
| Field | Value |
|-------|-------|
| Allow task to be run on demand | Checked |
| If the task is already running | Do not start a new instance |
| Stop the task if it runs longer than | 1 hour |

### Step 7 — Save
- Click **OK**
- If prompted, enter your Windows password to save the task

---

## Task 2 — Process Emails (Every 2 Hours)

### Step 1 — Open the Create Task dialog
- Click **"Create Task..."** in the Actions panel

### Step 2 — General tab
| Field | Value |
|-------|-------|
| Name | `AI Employee — Process Emails` |
| Description | `Processes pending email tasks in Needs_Action/ every 2 hours` |
| Run whether user is logged on or not | Selected |
| Run with highest privileges | Checked |

### Step 3 — Triggers tab
1. Click **"New..."**
2. Set the following:

| Field | Value |
|-------|-------|
| Begin the task | On a schedule |
| Settings | Daily |
| Start | Today's date, **6:00:00 AM** |
| Recur every | 1 day |
| Enabled | Checked |

3. Still in the New Trigger dialog, check **"Repeat task every:"**

| Field | Value |
|-------|-------|
| Repeat task every | `2 hours` |
| For a duration of | `18 hours` (covers 6 AM – midnight) |

4. Click **OK**

> **Tip:** Setting duration to "Indefinitely" is also valid if you want
> 24/7 processing, but 18 hours covers typical working + evening hours.

### Step 4 — Actions tab
1. Click **"New..."**

| Field | Value |
|-------|-------|
| Action | Start a program |
| Program/script | `D:\coding\hackaton\hac_0\AI_Employee_Vault\scheduled_tasks\process_emails.bat` |
| Add arguments | *(leave blank)* |
| Start in | `D:\coding\hackaton\hac_0\AI_Employee_Vault` |

2. Click **OK**

### Step 5 — Settings tab
| Field | Value |
|-------|-------|
| Allow task to be run on demand | Checked |
| If the task is already running | Do not start a new instance |
| Stop the task if it runs longer than | 30 minutes |

### Step 6 — Save
- Click **OK** and enter password if prompted

---

## Task 3 — Daily Summary (8:00 PM Daily)

### Step 1 — Open the Create Task dialog
- Click **"Create Task..."**

### Step 2 — General tab
| Field | Value |
|-------|-------|
| Name | `AI Employee — Daily Summary` |
| Description | `Creates end-of-day summary and updates Dashboard at 8 PM` |
| Run whether user is logged on or not | Selected |
| Run with highest privileges | Checked |

### Step 3 — Triggers tab
1. Click **"New..."**

| Field | Value |
|-------|-------|
| Begin the task | On a schedule |
| Settings | Daily |
| Start | Today's date, **8:00:00 PM** (20:00:00) |
| Recur every | 1 day |
| Enabled | Checked |

2. Click **OK**

### Step 4 — Actions tab
1. Click **"New..."**

| Field | Value |
|-------|-------|
| Action | Start a program |
| Program/script | `D:\coding\hackaton\hac_0\AI_Employee_Vault\scheduled_tasks\daily_summary.bat` |
| Add arguments | *(leave blank)* |
| Start in | `D:\coding\hackaton\hac_0\AI_Employee_Vault` |

2. Click **OK**

### Step 5 — Settings tab
| Field | Value |
|-------|-------|
| Allow task to be run on demand | Checked |
| If the task is already running | Do not start a new instance |
| Stop the task if it runs longer than | 1 hour |

### Step 6 — Save
- Click **OK**

---

## Testing the Tasks

### Method 1 — Run on demand from Task Scheduler
1. Find your task in Task Scheduler Library
2. Right-click the task → **"Run"**
3. The task will execute immediately
4. Check `scheduled_tasks\logs\` for the output log

### Method 2 — Double-click the .bat file directly
1. Open `scheduled_tasks\` in File Explorer
2. Double-click `morning_briefing.bat` (or whichever task)
3. A Command Prompt window will open and run the command
4. Output is both shown in the window and saved to `logs\`

### Method 3 — Run from Command Prompt
```cmd
cd D:\coding\hackaton\hac_0\AI_Employee_Vault
scheduled_tasks\morning_briefing.bat
scheduled_tasks\process_emails.bat
scheduled_tasks\daily_summary.bat
```

### Verifying a Successful Run
After running, check:
1. `scheduled_tasks\logs\` — a new `.log` file should appear with today's timestamp
2. The log file should end with `Result  : SUCCESS`
3. `Dashboard.md` — should have an updated "Last Updated" timestamp
4. `Logs\YYYY-MM-DD.md` — should have new log entries

### Checking Task History in Task Scheduler
1. Click on a task in the Library
2. Click the **"History"** tab at the bottom
3. Look for event ID 201 (Task completed) — exit code 0 = success
4. Event ID 203 (Task action failed) means the `.bat` returned an error

---

## Troubleshooting

### "claude is not recognized as an internal or external command"
The `claude` CLI is not on the system PATH for the account running the task.

**Fix:** Edit the `.bat` file and replace `claude` with the full path:
```bat
"C:\Users\YourName\AppData\Roaming\npm\claude" "your prompt here"
```
Find the full path by running `where claude` in Command Prompt.

### Task runs but produces empty output
The task may be running as SYSTEM which has no Claude config/auth.

**Fix:** In the task's General tab, select
**"Run only when user is logged on"** and ensure you're logged in when it runs.

Alternatively, set the task to run as your specific user account.

### Task says "The operator or administrator has refused the request"
Claude CLI may require interactive TTY for some operations.

**Fix:** Ensure the `.bat` file's `Start in` is set correctly to the vault root,
and that `claude` has been configured with API key via `claude config` first.

### Logs directory is empty after running
The task may have failed before reaching the logging code.

**Fix:** Check Windows Event Viewer → Windows Logs → Application for errors,
or run the `.bat` file manually from Command Prompt to see live output.

### Task runs at wrong time (timezone issues)
Task Scheduler uses the system timezone.

**Fix:** Verify your system clock and timezone in
Settings → Time & Language → Date & Time.

---

## Schedule Summary

| Task | File | Trigger | Log retention |
|------|------|---------|---------------|
| Morning Briefing | `morning_briefing.bat` | Daily 8:00 AM | 30 days |
| Process Emails | `process_emails.bat` | Every 2 hours, 6 AM–midnight | 14 days |
| Daily Summary | `daily_summary.bat` | Daily 8:00 PM | 30 days |

---

## Log File Naming Convention

Logs are saved in `scheduled_tasks\logs\` with the format:

```
{task_name}_{YYYY-MM-DD}_{HH-MM}.log
```

Examples:
```
morning_briefing_2026-02-19_08-00.log
process_emails_2026-02-19_10-00.log
daily_summary_2026-02-19_20-00.log
```

Old logs are automatically cleaned up by each `.bat` file using `forfiles`.

---

*AI Employee Vault — Silver Tier Phase 5 | Task Scheduler Automation*
