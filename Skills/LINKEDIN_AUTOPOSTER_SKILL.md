---
skill_name: LINKEDIN_AUTOPOSTER
version: 1.0
category: content_publishing
created: 2026-02-24
status: legacy
superseded_by: SOCIAL_MEDIA_AUTOPOSTER_SKILL
depends_on: [HITL_APPROVAL_SKILL, LOGGER_SKILL, DASHBOARD_UPDATER_SKILL]
---

# Agent Skill: LinkedIn Auto-Poster (Legacy — LinkedIn Only)

> **Note:** This skill documents `linkedin_auto_poster.py` (LinkedIn only).
> For the current Gold tier implementation covering LinkedIn, Facebook, Twitter,
> and Instagram, see **SOCIAL_MEDIA_AUTOPOSTER_SKILL.md**.


## Purpose
Autonomously generate, schedule, and manage LinkedIn post publication with mandatory human-in-the-loop approval. Produces data-driven professional content from vault activity statistics, rotates through four post types to maintain variety, and enforces quality gates before requesting approval.

---

## When To Use This Skill

| Trigger | Action |
|---------|--------|
| Today is Monday, Wednesday, or Friday near 10 AM | Run `--generate` to draft a post |
| LINKEDIN_POST_*.md found in Approved/ | Run `--check-approved` to execute |
| LINKEDIN_POST_*.md found in Rejected/ | Run `--check-approved` to log and clean up |
| Ralph's `--ralph-check` cycle | Run `--ralph-check` (handles both above automatically) |
| User requests a LinkedIn post | Run `--generate` or `--generate --dry-run` to preview |
| User asks for posting schedule | Run `--schedule` |
| User asks for status | Run `--status` |

---

## CLI Reference

```bash
# Generate a post draft + create approval request
python linkedin_auto_poster.py --generate

# Preview generation without writing files
python linkedin_auto_poster.py --generate --dry-run

# Generate the next 6-slot schedule (2 weeks, M/W/F)
python linkedin_auto_poster.py --schedule

# Execute all approved/rejected LinkedIn posts in queue
python linkedin_auto_poster.py --check-approved

# Show full status: queue, history, next slots
python linkedin_auto_poster.py --status

# Smart mode for Ralph's OODA loop (handles generate + check-approved)
python linkedin_auto_poster.py --ralph-check
```

---

## Post Types (Content Rotation)

| Type | Description | Posting Signal |
|------|-------------|----------------|
| `achievement` | Weekly metrics: emails, tasks, approvals, Ralph cycles | Data-driven, uses live vault stats |
| `thought_leadership` | HITL insights, OODA loop, automation tiers | Authoritative, 3 variants |
| `tip` | Practical AI automation advice | Educational, concise |
| `behind_the_scenes` | Live snapshot of the AI Employee system | Transparent, builds trust |

**Rotation rule:** Never post the same type twice in a row. The script selects the type not used in the last 3 posts.

---

## Approval Workflow

This skill strictly follows **HITL_APPROVAL_SKILL** for all posts.

```
linkedin_auto_poster.py --generate
        ↓
  Quality checks pass
        ↓
  Creates: Pending_Approval/LINKEDIN_POST_{id}_{date}.md
        ↓
  Human reviews content preview in approval file
        ↓
  ┌─ Move to Approved/  →  --check-approved  →  Post published → Done/
  └─ Move to Rejected/  →  --check-approved  →  Rejection logged → Done/
```

**Approval file location:** `Pending_Approval/LINKEDIN_POST_{8-char-id}_{YYYY-MM-DD}.md`
**Expiry:** 24 hours from creation (logged as timed out if not actioned)

---

## Quality Gates

Every post passes these checks before an approval file is created:

| Check | Threshold | Block? |
|-------|-----------|--------|
| Character count | ≤ 3000 (hard limit) | Yes |
| Character count | ≤ 1300 (recommended) | Warn only |
| Hook in first line | Non-empty | Yes |
| Hashtags | 1–10 (3–5 recommended) | Yes if 0 |
| Engagement CTA | Question or call-to-action | Warn only |
| Professional tone | No slang patterns | Warn only |
| Duplicate detection | >80% hashtag overlap with last 6 posts | Warn only |

---

## Ralph Integration

Add `linkedin_autoposter` to Ralph's action cycle. Ralph calls:

```
python linkedin_auto_poster.py --ralph-check
```

**`--ralph-check` logic:**
1. If `Approved/LINKEDIN_POST_*.md` exists → execute immediately
2. If `Rejected/LINKEDIN_POST_*.md` exists → clean up immediately
3. If today is Mon/Wed/Fri + near 10 AM + not yet posted today + under weekly cap → generate
4. Otherwise → no-op, exit cleanly

**Recommended ralph_config.json addition:**
```json
"actions": {
  "priority_queue": [
    "process_urgent_emails",
    "check_approval_expiry",
    "linkedin_autopost",          ← add this
    "process_normal_emails",
    ...
  ]
}
```

**Ralph prompt for linkedin_autopost action:**
> Check if the LinkedIn auto-poster needs to run. Execute: `python linkedin_auto_poster.py --ralph-check`. Log the outcome.

---

## Post History

All generated posts are tracked in `linkedin_post_history.json`:

```json
{
  "total_generated": 12,
  "total_posted": 9,
  "total_rejected": 3,
  "posts": [
    {
      "id": "ABC12345",
      "content_type": "achievement",
      "created_at": "2026-02-24T10:00:00Z",
      "status": "posted_simulated",
      "char_count": 483,
      "hashtags": ["#AIEmployee", "#Automation", ...],
      "approval_file": "Pending_Approval/LINKEDIN_POST_ABC12345_2026-02-24.md"
    }
  ]
}
```

Used for:
- Duplicate detection (avoid repeating content)
- Type rotation (prevent consecutive same-type posts)
- Weekly cap enforcement (max 3 posts/week)
- Reporting in `--status`

---

## Simulation vs Live Mode

| Setting | Behaviour |
|---------|-----------|
| `SIMULATION_MODE = True` (default) | Approval files created; no real LinkedIn API call; outcome logged as "simulated" |
| `SIMULATION_MODE = False` | Requires `LINKEDIN_ACCESS_TOKEN` env var; real API call on approval |

Both modes create identical approval files and history records. The only difference is whether the LinkedIn API is called.

To switch to live mode:
1. Set `SIMULATION_MODE = False` in `linkedin_auto_poster.py`
2. Set `SIMULATION_MODE = false` in `mcp_servers/linkedin_mcp/index.js`
3. Complete OAuth setup per `mcp_servers/linkedin_mcp/README.md`
4. Set environment: `LINKEDIN_ACCESS_TOKEN=...` + `LINKEDIN_PERSON_URN=...`

---

## Logging

Uses **LOGGER_SKILL** action types:

| Event | action_type |
|-------|-------------|
| Post generated | `linkedin_post_generated` |
| Post approved + published | `linkedin_post_published` |
| Post rejected | `linkedin_post_rejected` |
| Schedule created | `linkedin_schedule_created` |
| Quality check failed | `linkedin_quality_failed` |

Log entries written to `Logs/YYYY-MM-DD.md` automatically.

---

## Dashboard Integration

After generating or processing posts, update Dashboard.md:

- **Pending Approvals:** increment/decrement count
- **Recent Activity:** add entry in format:
  - `[HH:MM] LinkedIn post drafted: {content_type} (id: {post_id}) — awaiting approval`
  - `[HH:MM] LinkedIn post approved + published: {post_id} (simulated)`
  - `[HH:MM] LinkedIn post rejected: {post_id}`

---

## Error Handling

| Error | Response |
|-------|----------|
| Quality check FAIL | Log error, do not create approval file, report to human |
| Approval file write fails | Log error, do not add to history |
| `check-approved` — post not in history | Log warning, still move file to Done/ |
| Weekly cap reached | Log info, skip generation, report in status |
| SIMULATION_MODE mismatch with MCP server | Log warning, proceed (each component is independent) |

---

## Safety Rules

1. **NEVER publish without an approval file in Approved/** — no exceptions
2. **NEVER auto-approve** — the script cannot move its own files to Approved/
3. **NEVER post more than `MAX_POSTS_PER_WEEK`** (default: 3)
4. **ALWAYS run quality checks** before creating approval file
5. **ALWAYS log every action** — generated, approved, rejected, expired
6. **ALWAYS preserve audit trail** — resolved files end in Done/

---

*Skill Version: 1.0*
*AI Employee Vault Gold v1.0*
