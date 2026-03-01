---
skill_name: LOGGER
version: 1.0
category: utility
created: 2026-02-15
---

# Agent Skill: Logger

## Purpose
Create structured log entries for all AI Employee actions.

## Log Location
- Folder: Logs/
- Filename format: YYYY-MM-DD.md
- Example: Logs/2026-02-15.md

## Log Entry Format
```markdown
---
timestamp: [ISO 8601 timestamp]
action_type: [type]
actor: claude_code
status: [success/failed/pending]
---

## Action: [Action Name]

**Details:**
- File: [filename if applicable]
- Operation: [what was done]
- Result: [outcome]

**Notes:**
[Any additional context]

---
```

## Action Types
- file_processed
- file_created
- dashboard_updated
- file_moved
- error_occurred
- manual_intervention_required
- system_health_check
- batch_operation_completed

## Logging Rules

1. **Create log file** if doesn't exist for today
2. **Append new entries** (don't overwrite existing)
3. **Use ISO 8601 timestamps** (YYYY-MM-DDTHH:MM:SSZ)
4. **Include all relevant details** for audit trail
5. **Log errors with details** if available
6. **Separate entries** with --- divider

## Status Values
- success: Operation completed successfully
- failed: Operation encountered error
- pending: Operation awaiting approval or completion

## Example Log Entry
```markdown
---
timestamp: 2026-02-15T14:30:00Z
action_type: file_processed
actor: claude_code
status: success
---

## Action: File Processed

**Details:**
- File: FILE_document_2026-02-15.md
- Operation: Analyzed, categorized, and moved to Done
- Result: Successfully completed

**Notes:**
File contained test document. No issues found during processing.

---
```

## Daily Log Structure

Each daily log file should have:
- Header with date
- Multiple log entries
- Summary at end of day (if applicable)

Example:
```markdown
# Log: 2026-02-15

## Summary
- Total actions: 5
- Successful: 5
- Failed: 0
- Pending: 0

---

[Individual log entries follow]
```

---
*Skill Version: 1.0*
