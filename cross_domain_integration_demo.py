#!/usr/bin/env python3
"""
AI Employee Vault — Cross-Domain Integration Demo
==================================================
Gold Tier: Demonstrates full cross-domain integration spanning personal
and business domains via simulated MCP tool chains.

Domains:
  PERSONAL:  Gmail (personal), Filesystem (vault)
  BUSINESS:  Google Calendar, Google Drive, Business Gmail, Slack

Workflows demonstrated:
  1. Personal Email → Business Action
     Urgent personal email → Ralph creates plan → Calendar event → Slack update → Drive notes

  2. Business Meeting → Personal Reminder
     Business calendar event → Personal calendar block → Personal email reminder → Dashboard update

  3. CEO Briefing Distribution
     Aggregate personal + business data → Upload to Drive → Share via Slack → Calendar invite

Usage:
  python cross_domain_integration_demo.py --workflow 1
  python cross_domain_integration_demo.py --workflow 2
  python cross_domain_integration_demo.py --workflow 3
  python cross_domain_integration_demo.py --workflow all
  python cross_domain_integration_demo.py --workflow all --dry-run
"""

import argparse
import json
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

# Ensure UTF-8 output on Windows
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# ============================================================
# CONFIGURATION
# ============================================================

VAULT_PATH = Path(__file__).parent

PENDING_APPROVAL_DIR = VAULT_PATH / "Pending_Approval"
APPROVED_DIR         = VAULT_PATH / "Approved"
DONE_DIR             = VAULT_PATH / "Done"
PLANS_DIR            = VAULT_PATH / "Plans"
REPORTS_DIR          = VAULT_PATH / "Reports"
LOGS_DIR             = VAULT_PATH / "Logs"

# Simulation — all True for demo; matches MCP server flags
SIMULATE_ALL = True

# ============================================================
# UTILITIES
# ============================================================

def now_iso() -> str:
    return datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")

def today_str() -> str:
    return datetime.now().strftime("%Y-%m-%d")

def future_iso(days: int = 1, hour: int = 9) -> str:
    dt = datetime.now().replace(hour=hour, minute=0, second=0, microsecond=0)
    dt += timedelta(days=days)
    return dt.isoformat()

def hr(title: str = "") -> None:
    width = 60
    if title:
        print(f"\n{'=' * width}")
        print(f"  {title}")
        print(f"{'=' * width}")
    else:
        print(f"  {'-' * (width - 4)}")

def step(number: int, description: str) -> None:
    print(f"\n  [{number}] {description}")

def tool_call(server: str, tool: str, args: dict) -> dict:
    """Simulate an MCP tool call — prints the invocation and returns mock result."""
    args_preview = json.dumps(args, indent=None)[:120]
    print(f"      MCP CALL  {server}.{tool}({args_preview})")
    return {"simulation": True, "tool": tool, "server": server}

def approval_file(prefix: str, description: str, content: str, dry_run: bool = False) -> str:
    """Write a HITL approval file to Pending_Approval/."""
    filename = f"{prefix}_{today_str()}.md"
    filepath = PENDING_APPROVAL_DIR / filename
    if not dry_run:
        PENDING_APPROVAL_DIR.mkdir(parents=True, exist_ok=True)
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)
    print(f"      APPROVAL  Pending_Approval/{filename} — {description}")
    return filename

def plan_file(name: str, content: str, dry_run: bool = False) -> str:
    """Write a plan file to Plans/."""
    filename = f"PLAN_{name}_{today_str()}.md"
    filepath = PLANS_DIR / filename
    if not dry_run:
        PLANS_DIR.mkdir(parents=True, exist_ok=True)
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)
    print(f"      PLAN      Plans/{filename}")
    return filename

def log_workflow(workflow_id: int, step_name: str, result: str, dry_run: bool = False) -> None:
    """Append a log entry for the workflow action."""
    log_file = LOGS_DIR / f"{today_str()}.md"
    entry = f"""
---
timestamp: {now_iso()}
action_type: cross_domain_workflow
actor: cross_domain_integration_demo
workflow: {workflow_id}
step: {step_name}
status: {"simulated" if SIMULATE_ALL else "live"}
dry_run: {dry_run}
---

## Cross-Domain Workflow {workflow_id}: {step_name}

**Result:** {result}

---
"""
    if not dry_run:
        LOGS_DIR.mkdir(parents=True, exist_ok=True)
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(entry)

# ============================================================
# WORKFLOW 1: Personal Email → Business Action
# ============================================================
# Trigger: Urgent personal email detected by gmail_watcher.py
# Chain:   Email analysis → Ralph plan → Calendar event → Slack notification → Drive notes

def workflow_1(dry_run: bool = False) -> None:
    hr("WORKFLOW 1: Personal Email → Business Action")
    print("""
  Scenario: An urgent email arrives in the personal Gmail inbox.
  Ralph detects it, creates a response plan, schedules a business
  calendar event, notifies the team on Slack, and saves notes to Drive.

  Domains: Personal Gmail → Vault → Google Calendar → Slack → Google Drive
""")

    # ── Step 1: Personal Gmail detects urgent email ────────────────
    step(1, "Personal Gmail Watcher detects urgent email")
    print("""
      SOURCE: personal Gmail (gmail_watcher.py — already running)
      FILE:   Needs_Action/EMAIL_Q1_Board_Report_Action_Required_2026-02-27.md
      PRIORITY: urgent (subject contains "Action Required")
""")
    email_data = {
        "subject": "Q1 Board Report — Action Required",
        "sender":  "ceo@company.com",
        "priority": "urgent",
        "snippet": "Please prepare Q1 board report summary and distribute to stakeholders by Friday.",
        "received": now_iso(),
    }
    print(f"      EMAIL     From: {email_data['sender']}")
    print(f"                Subject: {email_data['subject']}")
    print(f"                Priority: {email_data['priority'].upper()}")

    # ── Step 2: Ralph creates a response plan ─────────────────────
    step(2, "Ralph (OODA: Orient) creates multi-step response plan")
    plan_content = f"""---
plan_name: Q1 Board Report Response
created: {today_str()}
status: active
priority: high
owner: ralph_wiggum
requires_approval: false
triggered_by: EMAIL_Q1_Board_Report_Action_Required
---

# Plan: Q1 Board Report Response

## Objective
Respond to CEO's urgent request for Q1 board report by Friday.

## Steps

- [x] **Step 1: Acknowledge email**
  - Status: Completed by Ralph in Cycle #9
  - Result: Email moved to Done/, flagged as urgent

- [ ] **Step 2: Schedule board report review meeting**
  - Tool: calendar_create_event (business calendar)
  - Approval required: Yes (HITL — external calendar action)

- [ ] **Step 3: Notify team via Slack**
  - Tool: send_channel_message → #leadership
  - Approval required: Yes (HITL — external communication)

- [ ] **Step 4: Save meeting notes template to Drive**
  - Tool: drive_upload_file
  - Approval required: Yes (HITL — external upload)

- [ ] **Step 5: Generate weekly CEO briefing**
  - Tool: python weekly_ceo_briefing.py
  - Approval required: No (internal operation)

## Timeline
| Phase | Steps | Target |
|-------|-------|--------|
| Immediate | 1-3 | Today |
| Friday | 4-5 | Before 5 PM |

---
*Generated by cross_domain_integration_demo.py — Workflow 1*
"""
    plan_name = plan_file("Q1_board_report_response", plan_content, dry_run)
    log_workflow(1, "plan_created", f"Plan: {plan_name}", dry_run)

    # ── Step 3: Create business calendar event ────────────────────
    step(3, "Create business calendar event (HITL approval required)")
    tool_call("google_workspace_mcp", "calendar_create_event", {
        "title": "Q1 Board Report Review",
        "description": "Review and finalise Q1 board report for distribution. Triggered by CEO urgent email.",
        "start_time": future_iso(days=2, hour=14),
        "end_time": future_iso(days=2, hour=15),
        "attendees": ["ceo@company.com", "cto@company.com", "cfo@company.com"],
        "send_notifications": True,
    })

    calendar_approval = f"""---
type: calendar_event_approval
action: create_calendar_event
created: {now_iso()}
expires: {(datetime.utcnow() + timedelta(hours=24)).strftime("%Y-%m-%dT%H:%M:%SZ")}
status: pending
risk_level: low
requested_by: cross_domain_integration_demo
workflow: 1
triggered_by: EMAIL_Q1_Board_Report_Action_Required
---

# Approval Request: Create Calendar Event

**Title:** Q1 Board Report Review
**Start:** {future_iso(days=2, hour=14)}
**End:**   {future_iso(days=2, hour=15)}
**Calendar:** Business (primary)

## Attendees
  - ceo@company.com
  - cto@company.com
  - cfo@company.com

## Triggered By
Personal email: "Q1 Board Report — Action Required" from ceo@company.com

## Mode
SIMULATION — no real Google Calendar API call

## To Approve → move to Approved/
## To Reject  → move to Rejected/

---
*Workflow 1: Personal Email → Business Action*
"""
    approval_file("CALENDAR_EVENT_WF1", "Q1 Board Report Review meeting", calendar_approval, dry_run)

    # ── Step 4: Notify team on Slack ──────────────────────────────
    step(4, "Post Slack team notification (HITL approval required)")
    slack_msg = (
        "*Action Required — Q1 Board Report*\n\n"
        "CEO has requested the Q1 board report summary by Friday.\n\n"
        "A review meeting has been scheduled for Wednesday 2–3 PM.\n"
        "Draft report should be ready by Tuesday EOD.\n\n"
        "AI Employee has created a task plan and will track progress."
    )
    tool_call("slack_mcp", "send_channel_message", {
        "channel": "#leadership",
        "message": slack_msg,
    })

    slack_approval = f"""---
type: slack_channel_approval
action: slack_send_message
created: {now_iso()}
expires: {(datetime.utcnow() + timedelta(hours=24)).strftime("%Y-%m-%dT%H:%M:%SZ")}
status: pending
risk_level: medium
requested_by: cross_domain_integration_demo
workflow: 1
---

# Approval Request: Slack Channel Message

**Channel:** #leadership

## Message Preview

---

{slack_msg}

---

## Mode
SIMULATION — no real Slack API call

## To Approve → move to Approved/
## To Reject  → move to Rejected/

---
*Workflow 1: Personal Email → Business Action*
"""
    approval_file("SLACK_MESSAGE_WF1", "Slack #leadership notification", slack_approval, dry_run)

    # ── Step 5: Upload meeting notes template to Drive ─────────────
    step(5, "Upload meeting notes template to Google Drive (HITL approval required)")
    tool_call("google_workspace_mcp", "drive_upload_file", {
        "file_path": "Reports/CEO_Briefing_2026-02-24.md",
        "title": "Q1 Board Report — Working Notes",
        "description": "Working notes for Q1 board report review. Auto-generated from vault.",
        "share_with": ["ceo@company.com", "cto@company.com"],
    })

    drive_approval = f"""---
type: drive_upload_approval
action: drive_upload_file
created: {now_iso()}
expires: {(datetime.utcnow() + timedelta(hours=24)).strftime("%Y-%m-%dT%H:%M:%SZ")}
status: pending
risk_level: medium
requested_by: cross_domain_integration_demo
workflow: 1
---

# Approval Request: Upload File to Google Drive

**Local file:** Reports/CEO_Briefing_2026-02-24.md
**Drive title:** Q1 Board Report — Working Notes
**Share with:** ceo@company.com, cto@company.com

## Mode
SIMULATION — no real Google Drive API call

## To Approve → move to Approved/
## To Reject  → move to Rejected/

---
*Workflow 1: Personal Email → Business Action*
"""
    approval_file("DRIVE_UPLOAD_WF1", "CEO briefing → Google Drive", drive_approval, dry_run)

    log_workflow(1, "workflow_complete", "3 approval files created, 1 plan created", dry_run)

    hr()
    print(f"""
  WORKFLOW 1 COMPLETE
  -------------------
  Domain chain: Personal Gmail → Vault Plan → Calendar + Slack + Drive
  Approval files created: 3
    - CALENDAR_EVENT_WF1_{today_str()}.md
    - SLACK_MESSAGE_WF1_{today_str()}.md
    - DRIVE_UPLOAD_WF1_{today_str()}.md
  Plan created: PLAN_Q1_board_report_response_{today_str()}.md

  Mode: {"DRY RUN — no files written" if dry_run else "SIMULATION — files created in Pending_Approval/ and Plans/"}
""")


# ============================================================
# WORKFLOW 2: Business Meeting → Personal Reminder
# ============================================================
# Trigger: New business calendar event detected
# Chain:   Calendar event → Personal email reminder → Dashboard update

def workflow_2(dry_run: bool = False) -> None:
    hr("WORKFLOW 2: Business Meeting → Personal Reminder")
    print("""
  Scenario: A business meeting is detected on the Google Calendar.
  The AI Employee creates a personal email reminder and updates the
  vault Dashboard with the upcoming commitment.

  Domains: Google Calendar → Business Gmail search → Personal Gmail → Dashboard
""")

    # ── Step 1: Read business calendar ────────────────────────────
    step(1, "Read business calendar for upcoming events")
    tool_call("google_workspace_mcp", "calendar_list_events", {
        "max_results": 5,
        "time_min": now_iso(),
        "time_max": future_iso(days=7),
    })

    meeting = {
        "title": "AI Employee Demo — Investor Presentation",
        "start": future_iso(days=3, hour=14),
        "end":   future_iso(days=3, hour=15),
        "attendees": ["investors@vc.com", "team@company.com"],
        "location": "Google Meet",
    }
    print(f"\n      FOUND     '{meeting['title']}'")
    print(f"                Start: {meeting['start']}")
    print(f"                Attendees: {', '.join(meeting['attendees'])}")

    # ── Step 2: Check business email for context ──────────────────
    step(2, "Search business Gmail for investor meeting context")
    tool_call("google_workspace_mcp", "gmail_business_search", {
        "query": "from:investors@vc.com subject:demo",
        "max_results": 3,
        "label_ids": ["INBOX"],
    })
    print("      RESULT    Found 1 email thread: 'Following the demo last week...'")

    # ── Step 3: Send personal email reminder ──────────────────────
    step(3, "Send personal email reminder (via email_mcp — HITL approval required)")
    reminder_body = f"""Hi,

This is an automated reminder from your AI Employee.

UPCOMING BUSINESS MEETING
Title:     {meeting['title']}
Date/Time: {meeting['start']}
Duration:  1 hour
Location:  {meeting['location']}
Attendees: {', '.join(meeting['attendees'])}

PREPARATION CHECKLIST:
  [ ] Review investor update email thread
  [ ] Prepare demo environment (run: python ralph_wiggum_loop.py --once)
  [ ] Have CEO briefing report ready (Reports/CEO_Briefing_2026-02-24.md)
  [ ] Test all MCP server connections

This reminder was generated by Ralph's OODA loop via Google Calendar integration.

-- AI Employee Vault
"""
    tool_call("email_mcp", "send_email", {
        "to": "personal@gmail.com",
        "subject": f"Reminder: {meeting['title']} in 3 days",
        "body": reminder_body,
    })

    email_approval = f"""---
type: email_approval
action: send_email
created: {now_iso()}
expires: {(datetime.utcnow() + timedelta(hours=24)).strftime("%Y-%m-%dT%H:%M:%SZ")}
status: pending
risk_level: medium
requested_by: cross_domain_integration_demo
workflow: 2
---

# Approval Request: Send Personal Email Reminder

**To:** personal@gmail.com
**Subject:** Reminder: {meeting['title']} in 3 days

## Email Preview

---

{reminder_body[:600]}...

---

## Mode
SIMULATION — no real Gmail API call

## To Approve → move to Approved/
## To Reject  → move to Rejected/

---
*Workflow 2: Business Meeting → Personal Reminder*
"""
    approval_file("EMAIL_REMINDER_WF2", "Personal email reminder for investor demo", email_approval, dry_run)

    # ── Step 4: Create Slack reminder for the team ────────────────
    step(4, "Create Slack reminder for team lead (HITL approval required)")
    tool_call("slack_mcp", "create_reminder", {
        "text": f"Prep for '{meeting['title']}' — ensure demo environment is running, CEO briefing is ready.",
        "time": future_iso(days=2, hour=17),
        "user_id": "U_TEAM_LEAD",
    })

    slack_reminder_approval = f"""---
type: slack_reminder_approval
action: slack_create_reminder
created: {now_iso()}
expires: {(datetime.utcnow() + timedelta(hours=24)).strftime("%Y-%m-%dT%H:%M:%SZ")}
status: pending
risk_level: low
requested_by: cross_domain_integration_demo
workflow: 2
---

# Approval Request: Create Slack Reminder

**For user:** U_TEAM_LEAD (team lead)
**At:** {future_iso(days=2, hour=17)}

## Reminder Text

---

Prep for '{meeting['title']}' — ensure demo environment is running, CEO briefing is ready.

---

## Mode
SIMULATION — no real Slack API call

## To Approve → move to Approved/
## To Reject  → move to Rejected/

---
*Workflow 2: Business Meeting → Personal Reminder*
"""
    approval_file("SLACK_REMINDER_WF2", "Team prep reminder for investor demo", slack_reminder_approval, dry_run)

    # ── Step 5: Update Dashboard ───────────────────────────────────
    step(5, "Update vault Dashboard with upcoming commitment")
    if not dry_run:
        db_path = VAULT_PATH / "Dashboard.md"
        if db_path.exists():
            db_content = db_path.read_text(encoding="utf-8")
            timestamp_line = f"**Last Updated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            activity_entry = f"- [{datetime.now().strftime('%H:%M')}] Cross-domain Workflow 2: Investor demo reminder created → 2 approval files pending"
            # Update timestamp
            import re
            db_content = re.sub(r"\*\*Last Updated:\*\*.*", timestamp_line, db_content)
            # Add activity entry
            db_content = db_content.replace(
                "## Recent Activity",
                f"## Recent Activity\n{activity_entry}"
            )
            db_path.write_text(db_content, encoding="utf-8")
    print("      UPDATED   Dashboard.md — upcoming commitment noted")

    log_workflow(2, "workflow_complete", "2 approval files created, Dashboard updated", dry_run)

    hr()
    print(f"""
  WORKFLOW 2 COMPLETE
  -------------------
  Domain chain: Google Calendar → Business Gmail → Personal Gmail + Slack → Dashboard
  Approval files created: 2
    - EMAIL_REMINDER_WF2_{today_str()}.md
    - SLACK_REMINDER_WF2_{today_str()}.md
  Dashboard: Updated with upcoming commitment

  Mode: {"DRY RUN — no files written" if dry_run else "SIMULATION — files created in Pending_Approval/"}
""")


# ============================================================
# WORKFLOW 3: CEO Briefing Distribution
# ============================================================
# Trigger: Weekly CEO briefing generated
# Chain:   Aggregate data → Upload to Drive → Share via Slack → Calendar invite

def workflow_3(dry_run: bool = False) -> None:
    hr("WORKFLOW 3: CEO Briefing Distribution")
    print("""
  Scenario: The weekly CEO briefing has been generated (weekly_ceo_briefing.py).
  The AI Employee uploads it to Google Drive, posts it to the leadership
  Slack channel, and schedules a calendar review meeting with stakeholders.

  Domains: Vault Reports → Google Drive → Slack → Google Calendar
""")

    # Find most recent briefing
    briefing_files = sorted(REPORTS_DIR.glob("CEO_Briefing_*.md")) if REPORTS_DIR.exists() else []
    if briefing_files:
        latest = briefing_files[-1]
        briefing_rel = f"Reports/{latest.name}"
    else:
        briefing_rel = "Reports/CEO_Briefing_2026-02-27.md"
    briefing_name = Path(briefing_rel).stem

    # ── Step 1: Search Drive for existing briefings ────────────────
    step(1, "Search Drive for existing CEO briefings (read-only)")
    tool_call("google_workspace_mcp", "drive_search_files", {
        "query": "name contains 'CEO_Briefing'",
        "max_results": 5,
    })
    print("      RESULT    Found 2 existing briefings in Drive")

    # ── Step 2: Upload this week's briefing ───────────────────────
    step(2, "Upload this week's CEO briefing to Google Drive (HITL approval required)")
    tool_call("google_workspace_mcp", "drive_upload_file", {
        "file_path": briefing_rel,
        "title": briefing_name,
        "description": "Weekly AI Employee business audit report. Auto-generated.",
        "share_with": ["ceo@company.com", "cto@company.com", "board@company.com"],
    })

    drive_upload = f"""---
type: drive_upload_approval
action: drive_upload_file
created: {now_iso()}
expires: {(datetime.utcnow() + timedelta(hours=24)).strftime("%Y-%m-%dT%H:%M:%SZ")}
status: pending
risk_level: medium
requested_by: cross_domain_integration_demo
workflow: 3
---

# Approval Request: Upload CEO Briefing to Google Drive

**Local file:** {briefing_rel}
**Drive title:** {briefing_name}
**Description:** Weekly AI Employee business audit report. Auto-generated.
**Share with:** ceo@company.com, cto@company.com, board@company.com

## Mode
SIMULATION — no real Google Drive API call

## To Approve → move to Approved/
## To Reject  → move to Rejected/

---
*Workflow 3: CEO Briefing Distribution*
"""
    approval_file("DRIVE_UPLOAD_WF3", f"CEO Briefing → Drive", drive_upload, dry_run)

    # ── Step 3: Share to Slack #leadership ───────────────────────
    step(3, "Post briefing announcement to Slack #leadership (HITL approval required)")
    slack_announcement = (
        f"*Weekly AI Employee CEO Briefing — {today_str()}*\n\n"
        f"This week's business audit report is ready for review.\n\n"
        f"*Key Highlights:*\n"
        f"- 117 tasks completed (0 pending)\n"
        f"- 110 emails processed autonomously\n"
        f"- Ralph: 8 autonomous cycles, 0 errors\n"
        f"- 3 HITL approvals resolved\n\n"
        f"Full report uploaded to Drive: `{briefing_name}`\n\n"
        f"Review meeting scheduled — see calendar invite."
    )
    tool_call("slack_mcp", "send_channel_message", {
        "channel": "#leadership",
        "message": slack_announcement,
    })

    slack_msg_approval = f"""---
type: slack_channel_approval
action: slack_send_message
created: {now_iso()}
expires: {(datetime.utcnow() + timedelta(hours=24)).strftime("%Y-%m-%dT%H:%M:%SZ")}
status: pending
risk_level: medium
requested_by: cross_domain_integration_demo
workflow: 3
---

# Approval Request: Slack #leadership Announcement

**Channel:** #leadership

## Message Preview

---

{slack_announcement}

---

## Mode
SIMULATION — no real Slack API call

## To Approve → move to Approved/
## To Reject  → move to Rejected/

---
*Workflow 3: CEO Briefing Distribution*
"""
    approval_file("SLACK_MESSAGE_WF3", "CEO briefing announcement → #leadership", slack_msg_approval, dry_run)

    # ── Step 4: Post briefing file to Slack ────────────────────────
    step(4, "Upload CEO briefing file directly to Slack (HITL approval required)")
    tool_call("slack_mcp", "post_file", {
        "channel": "#leadership",
        "file_path": briefing_rel,
        "title": f"CEO Briefing — {today_str()}",
        "initial_comment": "Attached: this week's full AI Employee business audit.",
    })

    slack_file_approval = f"""---
type: slack_file_upload_approval
action: slack_post_file
created: {now_iso()}
expires: {(datetime.utcnow() + timedelta(hours=24)).strftime("%Y-%m-%dT%H:%M:%SZ")}
status: pending
risk_level: medium
requested_by: cross_domain_integration_demo
workflow: 3
---

# Approval Request: Upload CEO Briefing File to Slack

**Channel:** #leadership
**File:** {briefing_rel}
**Title:** CEO Briefing — {today_str()}
**Comment:** Attached: this week's full AI Employee business audit.

## Mode
SIMULATION — no real Slack API call

## To Approve → move to Approved/
## To Reject  → move to Rejected/

---
*Workflow 3: CEO Briefing Distribution*
"""
    approval_file("SLACK_FILE_WF3", f"CEO briefing file → Slack #leadership", slack_file_approval, dry_run)

    # ── Step 5: Schedule review meeting on Calendar ────────────────
    step(5, "Schedule CEO briefing review meeting on business calendar (HITL approval required)")
    tool_call("google_workspace_mcp", "calendar_create_event", {
        "title": f"CEO Briefing Review — Week of {today_str()}",
        "description": (
            f"Weekly review of AI Employee business audit report.\n\n"
            f"Report: {briefing_name} (shared in #leadership Slack + uploaded to Drive)\n\n"
            f"Agenda:\n"
            f"1. Review key metrics\n"
            f"2. Outstanding approvals\n"
            f"3. Next week priorities"
        ),
        "start_time": future_iso(days=1, hour=10),
        "end_time": future_iso(days=1, hour=11),
        "attendees": ["ceo@company.com", "cto@company.com"],
        "send_notifications": True,
    })

    calendar_approval = f"""---
type: calendar_event_approval
action: create_calendar_event
created: {now_iso()}
expires: {(datetime.utcnow() + timedelta(hours=24)).strftime("%Y-%m-%dT%H:%M:%SZ")}
status: pending
risk_level: low
requested_by: cross_domain_integration_demo
workflow: 3
---

# Approval Request: Create Calendar Event

**Title:** CEO Briefing Review — Week of {today_str()}
**Start:** {future_iso(days=1, hour=10)}
**End:**   {future_iso(days=1, hour=11)}
**Calendar:** Business (primary)

## Attendees
  - ceo@company.com
  - cto@company.com

## Purpose
Review this week's AI Employee business audit report
(uploaded to Drive + posted to #leadership Slack).

## Mode
SIMULATION — no real Google Calendar API call

## To Approve → move to Approved/
## To Reject  → move to Rejected/

---
*Workflow 3: CEO Briefing Distribution*
"""
    approval_file("CALENDAR_EVENT_WF3", "CEO briefing review meeting", calendar_approval, dry_run)

    log_workflow(3, "workflow_complete", "4 approval files created", dry_run)

    hr()
    print(f"""
  WORKFLOW 3 COMPLETE
  -------------------
  Domain chain: Vault Reports → Google Drive → Slack (message + file) → Google Calendar
  Approval files created: 4
    - DRIVE_UPLOAD_WF3_{today_str()}.md
    - SLACK_MESSAGE_WF3_{today_str()}.md
    - SLACK_FILE_WF3_{today_str()}.md
    - CALENDAR_EVENT_WF3_{today_str()}.md

  Mode: {"DRY RUN — no files written" if dry_run else "SIMULATION — files created in Pending_Approval/"}
""")


# ============================================================
# SUMMARY
# ============================================================

def print_summary(workflows_run: list, dry_run: bool) -> None:
    hr("CROSS-DOMAIN INTEGRATION DEMO — SUMMARY")
    print(f"""
  Domains integrated:
    PERSONAL:  Gmail (personal inbox) via gmail_watcher.py
    BUSINESS:  Google Calendar  (calendar_list_events, calendar_create_event)
               Google Drive     (drive_search_files, drive_upload_file, drive_share_file)
               Business Gmail   (gmail_business_search)
               Slack            (send_channel_message, send_dm, post_file,
                                 get_mentions, create_reminder)

  MCP servers used:
    email_mcp              (1 tool)  — send_email
    google_workspace_mcp   (6 tools) — Calendar + Drive + Gmail Business
    slack_mcp              (5 tools) — Channel + DM + Files + Mentions + Reminders

  Workflows demonstrated: {', '.join(str(w) for w in workflows_run)}

  Approval files generated:
    Workflow 1: CALENDAR_EVENT + SLACK_MESSAGE + DRIVE_UPLOAD (3 files)
    Workflow 2: EMAIL_REMINDER + SLACK_REMINDER (2 files)
    Workflow 3: DRIVE_UPLOAD + SLACK_MESSAGE + SLACK_FILE + CALENDAR_EVENT (4 files)

  All operations use HITL (Human-in-the-Loop) approval.
  Move files from Pending_Approval/ to Approved/ to execute any action.

  Mode: {"DRY RUN — no files were written to disk" if dry_run else "SIMULATION — all approval files written to Pending_Approval/"}

  Next steps:
    1. Review approval files in Pending_Approval/
    2. Move approved items to Approved/
    3. Run: python social_media_auto_poster.py --check-approved
    4. For live mode: configure OAuth in mcp_servers/google_workspace_mcp/README.md
                      and bot token in mcp_servers/slack_mcp/README.md
""")


# ============================================================
# MAIN
# ============================================================

def main() -> None:
    parser = argparse.ArgumentParser(
        description="AI Employee Vault — Cross-Domain Integration Demo"
    )
    parser.add_argument(
        "--workflow", default="all",
        help="Workflow to run: 1, 2, 3, or all (default: all)"
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Preview all MCP tool calls without writing any files"
    )
    args = parser.parse_args()

    dry_run = args.dry_run
    workflows_run = []

    if dry_run:
        print("\n  [DRY RUN MODE] — No files will be written\n")

    if args.workflow in ("1", "all"):
        workflow_1(dry_run=dry_run)
        workflows_run.append(1)
    if args.workflow in ("2", "all"):
        workflow_2(dry_run=dry_run)
        workflows_run.append(2)
    if args.workflow in ("3", "all"):
        workflow_3(dry_run=dry_run)
        workflows_run.append(3)

    if not workflows_run:
        print(f"Unknown workflow: {args.workflow}. Use 1, 2, 3, or all.")
        sys.exit(1)

    print_summary(workflows_run, dry_run)


if __name__ == "__main__":
    main()
