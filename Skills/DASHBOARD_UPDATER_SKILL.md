---
skill_name: DASHBOARD_UPDATER
version: 1.0
category: core
created: 2026-02-15
---

# Agent Skill: Dashboard Updater

## Purpose
Update Dashboard.md with current system status, activity, and statistics.

## When to Use
- After processing files
- On manual request
- For daily summary
- System health check

## Update Sections

### 1. Today's Status
Count files in:
- Needs_Action/ → Pending Actions
- Done/ (with today's date in filename) → Completed Tasks
- Update System Status based on activity

### 2. Recent Activity
- Add new entries in reverse chronological order (newest first)
- Format: [HH:MM] [Action]: [Description]
- Keep last 10 entries only
- Remove older entries

### 3. Quick Stats
Calculate:
- Total files in Done/ → Total tasks processed
- Count files in Needs_Action/ → Files pending
- Count Done/ files with today's date → Files completed today

### 4. System Health
- Watcher Status: Check recent logs for watcher activity
- Last Check: Current timestamp in format YYYY-MM-DD HH:MM:SS

### 5. Last Updated
- Always update timestamp at top of Dashboard
- Format: YYYY-MM-DD HH:MM:SS

## Update Rules

1. **PRESERVE structure** - Don't change headers or layout
2. **INCREMENT numbers** - Don't replace, calculate correctly
3. **Format timestamps** - Use consistent format throughout
4. **Keep history** - In Recent Activity, keep last 10 entries
5. **Verify counts** - Double-check file counts before updating

## Safety

- Read current content first before modifying
- Make incremental changes only
- Don't delete existing data unless required (like old activity entries)
- If major update, keep backup comment in file

## Example Update

Before:
```markdown
## Today's Status
- **Pending Actions:** 3
- **Completed Tasks:** 5
```

After processing 2 files:
```markdown
## Today's Status
- **Pending Actions:** 1
- **Completed Tasks:** 7
```

---
*Skill Version: 1.0*
