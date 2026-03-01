---
skill_name: SOCIAL_MEDIA_AUTOPOSTER
version: 1.0
category: content_publishing
tier: Gold
created: 2026-02-27
depends_on: [HITL_APPROVAL_SKILL, LOGGER_SKILL, DASHBOARD_UPDATER_SKILL, RALPH_WIGGUM_SKILL]
supersedes: LINKEDIN_AUTOPOSTER_SKILL
---

# Agent Skill: Social Media Auto-Poster (v3.0 — 4 Platforms)

> Gold Tier: LinkedIn · Facebook · Twitter/X · Instagram

## Purpose

Autonomously generate, quality-check, schedule, and manage content publication
across four social media platforms with mandatory human-in-the-loop approval.
Content is derived from live vault activity data, rotated through four post types
for variety, and adapted to each platform's character limits, tone, and hashtag norms.

This skill covers both the **Python CLI** (`social_media_auto_poster.py`) and the
**MCP server** (`mcp_servers/social_media_mcp/` — 12 tools) which expose the same
functionality as Claude Code tools.

---

## Platform Coverage

| Platform | Content Style | Char Limit | Hashtags | Media |
|----------|--------------|------------|----------|-------|
| **LinkedIn** | Professional, data-driven | 3,000 (1,300 rec) | 3–5 | Optional |
| **Facebook** | Casual, conversational | 63,206 (80 rec) | 2–3 | Boosts reach 2.3x |
| **Twitter/X** | Punchy, thread-capable | 280/tweet | 1–2 | Optional |
| **Instagram** | Visual-first, aspirational | 2,200 | 20–25 in 1st comment | REQUIRED |

---

## Scripts and Tools

### Python CLI — `social_media_auto_poster.py`

```bash
# Generate a post for one or all platforms
python social_media_auto_poster.py --generate --platform linkedin
python social_media_auto_poster.py --generate --platform facebook
python social_media_auto_poster.py --generate --platform twitter
python social_media_auto_poster.py --generate --platform instagram
python social_media_auto_poster.py --generate --platform all

# Preview without writing files
python social_media_auto_poster.py --generate --platform all --dry-run

# Show the next 6 M/W/F posting slots
python social_media_auto_poster.py --schedule

# Process approved/rejected files in queue
python social_media_auto_poster.py --check-approved

# Full status — history, mode, next slots
python social_media_auto_poster.py --status

# Smart mode for Ralph's OODA loop
python social_media_auto_poster.py --ralph-check

# Cross-post to LinkedIn + Twitter + Instagram simultaneously
python social_media_auto_poster.py --cross-post
python social_media_auto_poster.py --cross-post --content "Custom message here"
```

### MCP Server — `mcp_servers/social_media_mcp/` (12 tools)

| # | Tool | Platform |
|---|------|----------|
| 1 | `create_linkedin_post` | LinkedIn |
| 2 | `schedule_linkedin_post` | LinkedIn |
| 3 | `generate_business_content` | LinkedIn |
| 4 | `create_twitter_post` | Twitter/X |
| 5 | `schedule_twitter_post` | Twitter/X |
| 6 | `create_instagram_post` | Instagram |
| 7 | `schedule_instagram_post` | Instagram |
| 8 | `create_facebook_post` | Facebook |
| 9 | `schedule_facebook_post` | Facebook |
| 10 | `cross_post_content` | LinkedIn + Twitter + Instagram |
| 11 | `cross_post` | LinkedIn + Facebook + Twitter |
| 12 | `generate_social_content` | All 4 platforms |

---

## Content Types (Rotation)

| Type | LinkedIn | Facebook | Twitter | Instagram |
|------|----------|----------|---------|-----------|
| `achievement` | Weekly metrics: emails, tasks, Ralph cycles | Casual metrics recap | Stats tweet thread | Stats caption |
| `thought_leadership` | HITL + OODA deep dive | Bold opinion post | Hot take tweet | Insight caption |
| `tip` | 3-step AI automation framework | Quick yes/no framework | Actionable tip | Save-this tip |
| `behind_the_scenes` | Architecture walkthrough | Casual system tour | Stack overview | "Behind the curtain" |

**Rotation rule:** Never repeat the same content type within the last 3 posts per platform.
Types rotate in order: achievement → thought_leadership → tip → behind_the_scenes → repeat.

---

## Posting Schedule

| Setting | Value |
|---------|-------|
| Days | Monday, Wednesday, Friday |
| Target time | 10:00 AM local |
| Window | ±90 minutes |
| Max per platform/week | 3 posts |
| Cap enforcement | Per-platform, independently tracked |

---

## Approval Workflow (HITL)

Each platform generates its own approval file. Cross-posting generates a single
combined file covering all selected platforms.

```
--generate (any platform)
       │
  Quality checks pass (see §Quality Gates)
       │
  Creates: Pending_Approval/{PLATFORM}_POST_{id}_{date}.md
       │
  Human reviews content preview in the approval file
       │
  ┌─ Move to Approved/  →  --check-approved  →  Post published → Done/
  └─ Move to Rejected/  →  --check-approved  →  Rejection logged → Done/
```

**Approval file naming:**

| Platform | Filename |
|----------|----------|
| LinkedIn | `LINKEDIN_POST_{id}_{date}.md` |
| Facebook | `FACEBOOK_POST_{id}_{date}.md` |
| Twitter | `TWITTER_POST_{id}_{date}.md` |
| Instagram | `INSTAGRAM_POST_{id}_{date}.md` |
| Cross-post (LI+TW+IG) | `CROSSPOST_{id}_{date}.md` |
| Cross-post (LI+FB+TW) | `CROSSPOST_LFT_{id}_{date}.md` |

---

## Quality Gates

Every post must pass these checks before an approval file is created:

### LinkedIn

| Check | Threshold | Block? |
|-------|-----------|--------|
| Character count | ≤ 3,000 | Yes |
| Character count | ≤ 1,300 (recommended) | Warn |
| Non-empty first line (hook) | Required | Yes |
| Hashtags present | ≥ 1 | Yes |
| CTA or question | Recommended | Warn |
| No slang patterns | OMG, LOL, gonna, etc. | Warn |

### Facebook

| Check | Threshold | Block? |
|-------|-----------|--------|
| Character count | ≤ 63,206 | Yes |
| Character count | ≤ 250 for text-only | Warn |
| Non-empty content | Required | Yes |
| CTA or question | Recommended | Warn |

### Twitter

| Check | Threshold | Block? |
|-------|-----------|--------|
| Each tweet | ≤ 280 chars | Yes |
| Hashtags | ≤ 3 (1–2 recommended) | Warn |

### Instagram

| Check | Threshold | Block? |
|-------|-----------|--------|
| Caption | ≤ 2,200 chars | Yes |
| Hashtags | ≤ 30 | Yes |
| Image URL | Required for live posting | Warn |

---

## Platform Adaption (Auto-formatting)

The poster automatically adapts content per platform:

| Platform | Adaptation |
|----------|-----------|
| LinkedIn | Professional tone, 5 hashtags, formatted with line breaks |
| Facebook | Casual tone, 2–3 hashtags, ends with direct question |
| Twitter | Thread split at 280 chars, `[N/M]` markers, 1–2 hashtags |
| Instagram | Hashtags separated to first comment, image URL required |

Twitter thread splitting: content is split at word boundaries with `[1/N]` suffix
markers added automatically. Hashtags appended to final tweet if they fit.

---

## Simulation vs Live Mode

| Flag | Behaviour |
|------|-----------|
| `SIMULATE_LINKEDIN = True` (default) | Creates approval file; no real LinkedIn API call |
| `SIMULATE_FACEBOOK = True` (default) | Creates approval file; no real Facebook Graph API call |
| `SIMULATE_TWITTER = True` (default) | Creates approval file; no real Twitter API v2 call |
| `SIMULATE_INSTAGRAM = True` (default) | Creates approval file; no real Instagram Graph API call |

All simulation flags are independent. To go live on one platform, flip its flag
and configure the required credentials (see `mcp_servers/social_media_mcp/README.md`
for full OAuth setup for each platform).

---

## Ralph Integration

Ralph calls the social media poster as part of its OODA action cycle:

```
python social_media_auto_poster.py --ralph-check
```

**`--ralph-check` logic (per platform: linkedin, facebook, twitter, instagram):**
1. Process any `Approved/{PLATFORM}_POST_*.md` files → execute (simulate)
2. Process any `Rejected/{PLATFORM}_POST_*.md` files → log + clean up
3. If today is Mon/Wed/Fri + in posting window + not yet posted today + under weekly cap → generate

**Recommended addition to `ralph_config.json`:**
```json
"actions": {
  "priority_queue": [
    "process_urgent_emails",
    "check_approval_expiry",
    "social_media_autopost",
    "process_normal_emails",
    ...
  ]
}
```

**Ralph prompt for `social_media_autopost`:**
> Check if the social media auto-poster needs to run. Execute:
> `python social_media_auto_poster.py --ralph-check`
> Log the outcome. If approval files were generated, note which platforms.

---

## Post History

All generated posts are tracked in `social_media_post_history.json` (v3.0):

```json
{
  "version": "3.0",
  "platforms": {
    "linkedin":  {"total_generated": 0, "total_approved": 0, "total_rejected": 0, "total_posted": 0},
    "facebook":  {"total_generated": 0, "total_approved": 0, "total_rejected": 0, "total_posted": 0},
    "twitter":   {"total_generated": 0, "total_approved": 0, "total_rejected": 0, "total_posted": 0},
    "instagram": {"total_generated": 0, "total_approved": 0, "total_rejected": 0, "total_posted": 0}
  },
  "posts": [...]
}
```

Used for: content rotation, duplicate detection, weekly cap enforcement, `--status` reporting.

---

## Logging

Uses **LOGGER_SKILL** with these action types:

| Event | `action_type` |
|-------|--------------|
| Post generated | `social_media_post` |
| Post approved + published | `social_media_post` (status: success) |
| Post rejected | `social_media_post` (status: rejected) |
| Quality check failed | `social_media_post` (status: failed) |

---

## Safety Rules

1. **NEVER publish without approval** — no post executes without a matching file in `Approved/`
2. **NEVER auto-approve** — the script cannot move its own files to `Approved/`
3. **NEVER exceed weekly cap** — 3 posts per platform per 7-day window
4. **ALWAYS run quality checks** — no approval file is created if quality checks fail
5. **ALWAYS log every action** — generated, approved, rejected, expired
6. **ALWAYS preserve audit trail** — all resolved approval files end up in `Done/`
7. **SIMULATION is the default** — real API calls require explicit flag change + credentials

---

## Legacy Note

`LINKEDIN_AUTOPOSTER_SKILL.md` documents the original LinkedIn-only implementation
(`linkedin_auto_poster.py`). That script remains present in the vault for reference.
This skill (SOCIAL_MEDIA_AUTOPOSTER_SKILL) is the current Gold tier implementation
covering all 4 platforms via `social_media_auto_poster.py` v3.0.

---

*Skill Version: 1.0 | Gold Tier | social_media_auto_poster.py v3.0 | social_media_mcp v3.0*
