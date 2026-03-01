---
skill_name: RALPH_WIGGUM_AUTONOMOUS_LOOP
version: 1.0
category: gold_tier
created: 2026-02-23
tier: Gold
---

# Agent Skill: Ralph Wiggum Autonomous Loop

> *"I'm helping!" — Ralph Wiggum*

## Purpose

Ralph Wiggum is the Gold tier autonomous reasoning engine. Unlike Bronze (manual triggers)
and Silver (scheduled triggers), Ralph runs continuously, thinks for himself, and decides
what to do next based on the current system state. He implements a full OODA cycle —
Observe, Orient, Decide, Act, Reflect — every configurable interval (default: 60 minutes).

Ralph is helpful, eager, and hardwired for safety. He will never send an email without
approval, never delete a file, and always creates plans before tackling complex tasks.

---

## OODA Cycle

```
┌─────────────────────────────────────────────────────────────┐
│                    RALPH WIGGUM LOOP                        │
│                                                             │
│   ┌──────────┐    ┌──────────┐    ┌──────────┐             │
│   │ OBSERVE  │───▶│  ORIENT  │───▶│  DECIDE  │             │
│   └──────────┘    └──────────┘    └──────────┘             │
│        ▲                                │                   │
│        │                               ▼                   │
│   ┌──────────┐    ┌──────────┐    ┌──────────┐             │
│   │ REFLECT  │◀───│   ACT    │◀───│ (action) │             │
│   └──────────┘    └──────────┘    └──────────┘             │
│                                                             │
│   ← ─ ─ ─ ─ ─ ─ ─ wait interval ─ ─ ─ ─ ─ ─ ─ ─ ─        │
└─────────────────────────────────────────────────────────────┘
```

---

## Phase 1 — OBSERVE

Ralph scans the vault to build a complete picture of current state.

### What Ralph checks:

| Source | What he reads | Why |
|--------|--------------|-----|
| `Needs_Action/` | File count, types, priorities, ages | Pending work |
| `Pending_Approval/` | Approval files, expiry times | Human decisions needed |
| `Plans/` | Active plans, completion status | Ongoing work |
| `Logs/ralph/ralph_state.json` | Last cycle time, action history | Continuity |
| `Dashboard.md` | System health indicators | Overall status |
| System clock | Time of day, day of week | Context for decisions |
| `Logs/YYYY-MM-DD.md` | Recent errors | System health |

### Observation Output (SystemSnapshot):
```python
{
  "needs_action": {
    "total": 12,
    "high_priority": 3,
    "normal": 8,
    "low": 1,
    "oldest_age_hours": 48,
    "types": {"EMAIL": 10, "FILE": 2}
  },
  "pending_approvals": {
    "count": 1,
    "expiring_soon": 0
  },
  "active_plans": 0,
  "time_context": "morning",
  "is_quiet_hours": false,
  "errors_in_log": 0
}
```

---

## Phase 2 — ORIENT

Ralph analyses the snapshot and scores each possible action by urgency.

### Scoring Rules:

| Condition | Score Modifier |
|-----------|---------------|
| High-priority item (emergency keyword) | +100 per item |
| Normal-priority item | +50 per item |
| Item age bonus | +2 per hour old |
| Approval expiring < 4 hours | +200 |
| Morning window (8–9:30 AM) | Boost morning briefing |
| Evening window (8–9:30 PM) | Boost evening summary |
| Quiet hours (11 PM – 6 AM) | All action scores → 0 |

### Context Labels:
- `morning` — 6 AM to 12 PM
- `afternoon` — 12 PM to 6 PM
- `evening` — 6 PM to 11 PM
- `quiet` — 11 PM to 6 AM (observe only)

---

## Phase 3 — DECIDE

Ralph picks from a prioritised action queue, selecting the highest-scoring
available action. He picks up to `max_actions_per_cycle` (default: 3) actions
per cycle, but executes them one at a time.

### Action Priority Queue (default order):

| Priority | Action | Trigger Condition |
|----------|--------|-------------------|
| 1 | `process_urgent_emails` | High-priority EMAIL_* in Needs_Action/ |
| 2 | `check_approval_expiry` | Approvals expiring within 4 hours |
| 3 | `process_normal_emails` | EMAIL_* files in Needs_Action/ |
| 4 | `generate_morning_briefing` | First cycle in morning window |
| 5 | `create_plan_for_complex_items` | More than 5 items needing action |
| 6 | `generate_evening_summary` | First cycle in evening window |
| 7 | `update_dashboard` | Dashboard hasn't been updated in 2+ hours |
| 8 | `health_check` | Errors found in recent logs |

### Decision Log Entry:
```
[DECIDE] 2026-02-23T08:01:00Z
  Scores: process_urgent_emails=156, generate_morning_briefing=90, update_dashboard=40
  Selected: process_urgent_emails (score=156)
  Reason: 3 high-priority items in Needs_Action/, oldest is 48 hours old
  Confidence: HIGH
```

---

## Phase 4 — ACT

Ralph executes the chosen action by invoking `claude "..."` as a subprocess.

### Claude Code Commands Used:

| Action | Claude Prompt |
|--------|--------------|
| `process_urgent_emails` | `"Process all HIGH priority pending email tasks in Needs_Action using FILE_PROCESSOR_SKILL. Focus on urgent items first."` |
| `process_normal_emails` | `"Process all pending email tasks in Needs_Action using FILE_PROCESSOR_SKILL"` |
| `generate_morning_briefing` | `"Generate morning briefing with pending tasks and recent emails"` |
| `generate_evening_summary` | `"Create end-of-day summary with stats and update Dashboard"` |
| `create_plan_for_complex_items` | `"Review items in Needs_Action and create a plan using PLAN_CREATOR_SKILL for complex multi-step items"` |
| `check_approval_expiry` | `"Check Pending_Approval folder for any approvals expiring within 4 hours and flag them in Dashboard"` |
| `update_dashboard` | `"Update Dashboard.md with current system status and recent activity"` |
| `health_check` | `"Check system health: review recent logs for errors, verify watchers are running, update Dashboard system health section"` |

### Safety Gates (checked before ANY action):
1. Is it quiet hours? → Skip all actions, log observation only
2. Does the action involve email sending? → Verify approval file exists in `Approved/`
3. Does the action involve deletion? → ABORT, log warning
4. Is `consecutive_errors >= 3`? → Pause and alert

---

## Phase 5 — REFLECT

After each action, Ralph evaluates what happened and updates state.

### Reflection Questions:
1. Did the action succeed? (exit code 0 = yes)
2. Did it reduce the number of pending items?
3. Were there unexpected errors?
4. What should the next cycle focus on?
5. Am I helping? *(Ralph check)*

### State Update:
- Increment `cycle_count`
- Record `last_action` with result
- Reset `consecutive_errors` on success
- Append to daily summary

---

## Logging

### Ralph Log Files:
```
Logs/ralph/
├── ralph_state.json          # Persisted state between restarts
├── 2026-02-23.log            # Detailed cycle log (one per day)
└── .gitkeep
```

### Log Entry Format:
```
[2026-02-23T08:01:00Z] [OBSERVE]  Needs_Action: 12 items (3 high, 8 normal, 1 low)
[2026-02-23T08:01:01Z] [ORIENT]   Scoring complete. Top action: process_urgent_emails (156)
[2026-02-23T08:01:01Z] [DECIDE]   Action selected: process_urgent_emails
[2026-02-23T08:01:02Z] [ACT]      Invoking claude... (timeout: 300s)
[2026-02-23T08:03:45Z] [ACT]      Completed. Exit code: 0. Duration: 163s
[2026-02-23T08:03:45Z] [REFLECT]  Success. Needs_Action reduced from 12 → 9. I'm helping!
[2026-02-23T08:03:45Z] [HEARTBEAT] Cycle #47 complete. Next cycle in 60 minutes.
```

---

## Safety Rules

1. **NEVER send email without approval** — check `Approved/` folder first
2. **NEVER delete files** — only move to `Done/` or `Rejected/`
3. **ALWAYS plan multi-step tasks** — use `PLAN_CREATOR_SKILL` for complex items
4. **ALWAYS log decisions** — every cycle produces a log entry
5. **NEVER act during quiet hours** — 11 PM to 6 AM is monitoring only
6. **PAUSE on repeated errors** — 3 consecutive errors trigger a pause + alert
7. **HUMAN in the loop** — sensitive actions always create approval requests

---

## Configuration (ralph_config.json)

All Ralph parameters are tunable without code changes:

| Parameter | Default | Description |
|-----------|---------|-------------|
| `loop.interval_minutes` | 60 | How often Ralph runs a cycle |
| `loop.max_actions_per_cycle` | 3 | Max Claude invocations per cycle |
| `loop.claude_timeout_seconds` | 300 | Abort if Claude takes too long |
| `quiet_hours.start_hour` | 23 | Quiet hours begin (11 PM) |
| `quiet_hours.end_hour` | 6 | Quiet hours end (6 AM) |
| `priorities.age_bonus_per_hour` | 2 | Score bonus per hour item is old |
| `priorities.approval_expiry_urgent_hours` | 4 | Hours before expiry = urgent |

---

## Ralph State (Persisted Between Restarts)

`Logs/ralph/ralph_state.json` preserves Ralph's memory across restarts:

```json
{
  "cycle_count": 47,
  "started_at": "2026-02-23T07:00:00Z",
  "last_cycle_at": "2026-02-23T14:00:00Z",
  "last_action": "process_normal_emails",
  "last_action_result": "success",
  "consecutive_errors": 0,
  "actions_today": ["generate_morning_briefing", "process_urgent_emails"],
  "briefing_done_today": true,
  "summary_done_today": false,
  "total_items_processed": 23
}
```

---

## Starting Ralph

```bash
# Start the autonomous loop
python ralph_wiggum_loop.py

# Start with custom config
python ralph_wiggum_loop.py --config ralph_config.json

# Dry run (observe + decide, but don't act)
python ralph_wiggum_loop.py --dry-run

# Single cycle then exit
python ralph_wiggum_loop.py --once
```

## Stopping Ralph

Press `Ctrl+C` — Ralph will complete the current action, log a clean shutdown,
and save state before exiting. He will resume from saved state on next start.

---

*"I'm Ralph, and I help things." — Gold Tier Autonomous Agent v1.0*

---
*Skill Version: 1.0 | Gold Tier*
