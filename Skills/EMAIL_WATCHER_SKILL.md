---
skill_name: EMAIL_WATCHER
version: 1.0
category: integration
tier: Silver
created: 2026-02-27
depends_on: [FILE_PROCESSOR_SKILL, LOGGER_SKILL, DASHBOARD_UPDATER_SKILL]
---

# Agent Skill: Email Watcher (Gmail Integration)

## Purpose

The Email Watcher monitors a Gmail inbox continuously, converts new unread emails
into structured markdown task files in `Needs_Action/`, and marks them as read so
they are never processed twice. It is the vault's primary ingestion point for all
email-driven work.

This is a **Silver tier** integration skill. It runs as a background process
alongside Ralph's autonomous loop.

---

## Script

```
gmail_watcher.py
```

---

## How It Works

```
Gmail Inbox (unread)
       │
       ▼ (every 5 minutes via POLL_INTERVAL)
gmail_watcher.py
       │
       ├─ Authenticate with OAuth 2.0 (credentials.json → token.json)
       ├─ Fetch unread emails (gmail.readonly scope)
       ├─ For each email:
       │    ├─ Parse sender, subject, date, body snippet
       │    ├─ Classify priority (urgent/normal/promotional)
       │    ├─ Generate EMAIL_*.md file in Needs_Action/
       │    └─ Mark email as read (gmail.modify scope)
       └─ Wait POLL_INTERVAL seconds → repeat
```

---

## Output File Format

Each email produces one file in `Needs_Action/`:

**Filename:** `EMAIL_{subject_slug}_{YYYY-MM-DD}.md`

**Example:** `Needs_Action/EMAIL_Action_needed_cluster_deletion_2026-02-18.md`

**Content structure:**
```markdown
---
type: email
original_subject: "Action needed: cluster deletion in 7 days"
sender: noreply@example.com
received: 2026-02-18T08:23:00Z
priority: normal
status: pending
---

# Email: Action needed: cluster deletion in 7 days

**From:** noreply@example.com
**Received:** 2026-02-18 08:23

## Content

[Email body / snippet]

## Required Action

[AI Employee analysis of what action this email requires]
```

---

## Priority Classification

| Label | Trigger Keywords | Action |
|-------|-----------------|--------|
| `urgent` | urgent, ASAP, critical, emergency, action required, immediately | Processed first by Ralph |
| `normal` | (default — no trigger keywords) | Standard processing queue |
| `promotional` | unsubscribe, newsletter, offer, deal, sale | Low priority, may be auto-archived |

---

## Gmail API Setup

### Credentials (one-time setup)

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create project → Enable **Gmail API**
3. Create **OAuth 2.0 Desktop credentials** → download as `credentials.json`
4. Place `credentials.json` in vault root
5. First run opens browser for OAuth consent → saves `token.json` automatically

### Scopes Required

| Scope | Purpose |
|-------|---------|
| `gmail.readonly` | Read email content and metadata |
| `gmail.modify` | Mark emails as read after ingestion |

### Environment

```bash
# credentials.json and token.json must be in vault root
# No other environment variables needed
```

---

## Usage

```bash
# Start the watcher (runs continuously, Ctrl+C to stop)
python gmail_watcher.py

# Start via wrapper script (Task Scheduler / background)
run_gmail_watcher.bat
```

---

## Polling Behaviour

| Parameter | Default | Notes |
|-----------|---------|-------|
| `POLL_INTERVAL` | 300 seconds (5 min) | Configurable at top of script |
| `VAULT_PATH` | Script directory | Automatically resolved |
| `NEEDS_ACTION_PATH` | `Needs_Action/` | Where EMAIL_*.md files go |

---

## Integration with Ralph

Ralph does **not** run the Gmail Watcher — they are independent processes.

The watcher deposits `EMAIL_*.md` files into `Needs_Action/`. Ralph's OBSERVE
phase detects them and schedules `process_normal_emails` or `process_urgent_emails`
actions to handle them via **FILE_PROCESSOR_SKILL**.

```
gmail_watcher.py    →    Needs_Action/EMAIL_*.md    →    Ralph processes via FILE_PROCESSOR_SKILL
(background daemon)      (shared vault inbox)             (OODA loop, HITL enforced)
```

**Ralph does not need to know about Gmail** — it only sees the generated files.

---

## Logging

The watcher logs to `Logs/YYYY-MM-DD.md` for each email ingested:

```
action_type: email_ingested
actor: gmail_watcher
status: success
```

Errors (OAuth failure, API quota, network) are logged with `status: failed`.

---

## Safety Rules

1. **NEVER delete emails** — only marks as read in Gmail
2. **NEVER modify email content** — body is copied verbatim into the task file
3. **ONLY write to Needs_Action/** — never writes to Done/, Approved/, or any other vault folder
4. **MARK AS READ immediately** after file creation — prevents duplicate ingestion
5. **LOG all actions** — every email ingested gets a log entry
6. **NEVER send email** — watcher is read-only inbound only; sending requires HITL_APPROVAL_SKILL

---

## Error Handling

| Error | Response |
|-------|----------|
| OAuth token expired | Refresh automatically via `token.json`; re-auth if refresh fails |
| Gmail API quota exceeded | Log error, wait POLL_INTERVAL, retry |
| Network timeout | Log warning, continue with next poll cycle |
| File write error (Needs_Action/) | Log error with full path, do NOT mark email as read |
| Malformed email (no subject/sender) | Use fallback values, log warning |

---

## File Produced vs Files Consumed

| Direction | Files |
|-----------|-------|
| **Produces** | `Needs_Action/EMAIL_{slug}_{date}.md` |
| **Marks read** | Gmail messages (not a vault file) |
| **Reads** | `credentials.json`, `token.json` (OAuth) |
| **Never touches** | `Done/`, `Approved/`, `Rejected/`, `Pending_Approval/`, `Plans/` |

---

## Automation

```
TASK_SCHEDULER_SETUP.md → Task 2: Gmail Watcher
run_gmail_watcher.bat   → Wrapper script with logging
```

Recommended: start at system boot, restart on failure (configured in Task Scheduler).

---

*Skill Version: 1.0 | Silver Tier | gmail_watcher.py*
