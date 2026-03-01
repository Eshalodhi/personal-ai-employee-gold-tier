---
skill_name: WEEKLY_CEO_BRIEFING
version: 1.0
category: gold_tier
created: 2026-02-23
tier: Gold
---

# Agent Skill: Weekly CEO Briefing Generator

## Purpose

Generates a comprehensive weekly business audit report covering all AI Employee
activity from the past 7 days. The report is written in clean markdown and saved
to `Reports/CEO_Briefing_YYYY-MM-DD.md` for review by the CEO or team lead.

This is a Gold tier reporting skill that aggregates data from all vault sources:
daily logs, email task files, approval records, and Ralph autonomous cycle logs.

---

## Output Format

The briefing produces a 5-section markdown report:

```
Reports/CEO_Briefing_YYYY-MM-DD.md
│
├── 1. Executive Summary      — at-a-glance table + key insights
├── 2. Key Metrics            — daily breakdown table, action types, success rates
├── 3. Email Analysis         — volume, priority breakdown, top senders/domains
├── 4. Ralph Autonomous       — OODA cycles, actions taken, success rate, recent cycles
└── 5. Upcoming Week Preview  — pending approvals, high-priority backlog, recommendations
```

---

## Usage

```bash
# Generate for the last 7 days (default)
python weekly_ceo_briefing.py

# Generate for a specific week-end date
python weekly_ceo_briefing.py --date 2026-02-23

# Custom lookback window (e.g. bi-weekly)
python weekly_ceo_briefing.py --days 14

# Print to console instead of saving
python weekly_ceo_briefing.py --stdout

# Combine flags
python weekly_ceo_briefing.py --date 2026-02-23 --stdout
```

---

## Data Sources

| Source | What is read | Metric produced |
|--------|-------------|-----------------|
| `Logs/YYYY-MM-DD.md` | Daily log files | Actions, success/fail counts |
| `Needs_Action/EMAIL_*.md` | Pending email tasks | Email pending count, senders, priorities |
| `Done/EMAIL_*.md` | Processed email tasks | Email clearance rate |
| `Done/APPROVAL_*.md` | Completed approvals | Approval accept rate |
| `Pending_Approval/APPROVAL_*.md` | Pending approvals | Items needing human decision |
| `Approved/APPROVAL_*.md` | Approved items | Approval outcome tracking |
| `Rejected/APPROVAL_*.md` | Rejected items | Rejection count |
| `Plans/PLAN_*.md` | Active plans | Plans created this week |
| `Logs/ralph/YYYY-MM-DD.log` | Ralph cycle logs | Autonomous cycles, actions, performance |

---

## Scheduling

The CEO briefing is designed to run **every Sunday** to cover the preceding 7 days.

### Recommended: Windows Task Scheduler

Refer to `TASK_SCHEDULER_SETUP.md` in the vault root for full Task Scheduler setup.
The briefing launcher is pre-configured as:

```
run_ceo_briefing.bat     (Task 3 in TASK_SCHEDULER_SETUP.md — Sunday 6 AM trigger)
```

### Manual Trigger

Ralph will also call `generate_morning_briefing` on Sunday mornings when
`weekly_ceo_briefing.py` is in scope. You can also simply run:

```bash
python weekly_ceo_briefing.py
```

---

## Sample Report Structure

```markdown
# AI Employee — Weekly CEO Briefing

**Week:** February 17 – February 23, 2026
**Generated:** 2026-02-23 10:45:00
**System:** AI Employee Vault (Gold Tier v1.0.0-gold)

---

## 1. Executive Summary

| Category | This Week |
|----------|----------|
| Total Actions | 42 |
| Success Rate | 98% |
| Emails Processed | 18 |
| Emails Pending | 16 |
| Approvals Requested | 3 |
| Approvals Granted | 3 |
| Ralph Autonomous Cycles | 0 |
| Plans Active | 1 |

### Key Insights

- AI Employee completed **41** of **42** actions with a **98%** success rate.
- Email pipeline processed **18** of **34** email tasks (**53%** clearance rate).
- Human approved **3** of **3** requests (**100%** approval rate).
- Ralph autonomous loop has not run yet — start with `python ralph_wiggum_loop.py`.

## 2. Key Metrics
...

## 3. Email Analysis
...

## 4. Ralph Autonomous Actions
...

## 5. Upcoming Week Preview
...
```

---

## Integration with Ralph

Ralph's autonomous loop (`ralph_wiggum_loop.py`) will call:
```
generate_morning_briefing
```
on Sunday mornings (08:00–09:30 local time) which can be extended to invoke
the CEO briefing script directly. To enable this, update the Claude prompt for
`generate_morning_briefing` in `ralph_config.json` to include:

```
"Generate morning briefing ... and if today is Sunday, also run python weekly_ceo_briefing.py"
```

---

## Output Location

All reports are saved to:
```
Reports/
└── CEO_Briefing_2026-02-23.md
└── CEO_Briefing_2026-03-02.md
└── ...
```

The `Reports/` directory is tracked by git for audit purposes.

---

*Skill Version: 1.0 | Gold Tier | weekly_ceo_briefing.py v1.0.0-gold*
