#!/usr/bin/env python3
"""
AI Employee Vault - LinkedIn Auto-Poster
=========================================
Gold Tier: Autonomous LinkedIn content generation and posting workflow.

Generates professional LinkedIn posts from vault activity data, creates
HITL approval requests, and executes approved posts (simulated or live).

Designed to run inside Ralph's OODA loop OR as a standalone script.

Usage:
  python linkedin_auto_poster.py --generate         # Generate today's post draft
  python linkedin_auto_poster.py --schedule         # Schedule next 6 posts (M/W/F)
  python linkedin_auto_poster.py --check-approved   # Execute any approved posts
  python linkedin_auto_poster.py --status           # Show queue and history
  python linkedin_auto_poster.py --ralph-check      # Smart check for Ralph's loop
  python linkedin_auto_poster.py --dry-run          # Preview without writing files
"""

import argparse
import io
import json
import os
import random
import re
import sys
from datetime import datetime, timedelta
from pathlib import Path

# Ensure UTF-8 output on Windows (cp1252 cannot encode emoji)
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# ============================================================
# CONFIGURATION
# ============================================================

VAULT_PATH = Path(__file__).parent

# Matches the SIMULATION_MODE flag in mcp_servers/linkedin_mcp/index.js
# Set to False only when the LinkedIn MCP server is also in LIVE mode.
SIMULATION_MODE = True

# Posting schedule: Mon=0, Wed=2, Fri=4 at 10:00 AM local time
POSTING_DAYS = {0: "Monday", 2: "Wednesday", 4: "Friday"}
POSTING_HOUR = 10
POSTING_WINDOW_MINUTES = 90  # ±90 min around 10 AM counts as posting time

# Post frequency: generate if fewer than this many posts were made this week
MAX_POSTS_PER_WEEK = 3

# Content rotation order — stays fresh by cycling through all 4 types
CONTENT_TYPES = ["achievement", "thought_leadership", "tip", "behind_the_scenes"]

# LinkedIn character limits (from linkedin_templates.json)
CHAR_LIMIT_HARD = 3000
CHAR_LIMIT_RECOMMENDED = 1300

# File paths
HISTORY_FILE = VAULT_PATH / "linkedin_post_history.json"
TEMPLATES_FILE = VAULT_PATH / "mcp_servers" / "linkedin_mcp" / "linkedin_templates.json"
RALPH_STATE_FILE = VAULT_PATH / "Logs" / "ralph" / "ralph_state.json"
PENDING_APPROVAL_DIR = VAULT_PATH / "Pending_Approval"
APPROVED_DIR = VAULT_PATH / "Approved"
REJECTED_DIR = VAULT_PATH / "Rejected"
DONE_DIR = VAULT_PATH / "Done"
LOGS_DIR = VAULT_PATH / "Logs"

# Hashtag sets (aligned with linkedin_templates.json categories)
HASHTAGS_AI = ["#AI", "#ArtificialIntelligence", "#GenerativeAI", "#LLM"]
HASHTAGS_AUTOMATION = ["#Automation", "#AIEmployee", "#Productivity", "#WorkSmarter"]
HASHTAGS_TECH = ["#Tech", "#Innovation", "#DigitalTransformation", "#FutureOfWork"]
HASHTAGS_LEADERSHIP = ["#Leadership", "#Management", "#Strategy", "#Business"]

# Quality check: words that signal unprofessional tone
UNPROFESSIONAL_PATTERNS = [
    r"\bOMG\b", r"\bWTF\b", r"\bLOL\b", r"\blol\b",
    r"\bkinda\b", r"\bgonna\b", r"\bwanna\b", r"\blegit\b",
    r"!!!", r"\?\?\?",
]

# ============================================================
# UTILITIES
# ============================================================

def now_iso() -> str:
    return datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")

def today_str() -> str:
    return datetime.now().strftime("%Y-%m-%d")

def today_time_str() -> str:
    return datetime.now().strftime("%H:%M")

def generate_post_id() -> str:
    """8-character hex post ID."""
    return format(random.randint(0, 0xFFFFFFFF), "08X")

def log_action(message: str, action_type: str = "linkedin_post", status: str = "success") -> None:
    """Append a structured entry to today's log file."""
    log_file = LOGS_DIR / f"{today_str()}.md"
    LOGS_DIR.mkdir(parents=True, exist_ok=True)

    entry = f"""
---
timestamp: {now_iso()}
action_type: {action_type}
actor: linkedin_auto_poster
status: {status}
---

## Action: LinkedIn Auto-Poster — {message}

**Details:**
- Script: linkedin_auto_poster.py
- Mode: {"SIMULATION" if SIMULATION_MODE else "LIVE"}
- Result: {status}

---
"""
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(entry)


def print_section(title: str) -> None:
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")


def print_info(label: str, value) -> None:
    print(f"  {label:<30} {value}")


# ============================================================
# DATA LOADING
# ============================================================

def load_post_history() -> dict:
    """Load post history from linkedin_post_history.json."""
    if not HISTORY_FILE.exists():
        return {
            "version": "1.0",
            "created": now_iso(),
            "last_updated": now_iso(),
            "total_generated": 0,
            "total_approved": 0,
            "total_rejected": 0,
            "total_posted": 0,
            "posts": [],
        }
    with open(HISTORY_FILE, encoding="utf-8") as f:
        return json.load(f)


def save_post_history(history: dict) -> None:
    """Write post history to disk."""
    history["last_updated"] = now_iso()
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(history, f, indent=2)


def load_vault_stats() -> dict:
    """Collect live stats from vault folder counts and ralph state."""
    def count_files(directory: Path, prefix: str = "") -> int:
        if not directory.exists():
            return 0
        return sum(
            1 for f in directory.iterdir()
            if f.is_file() and f.name.startswith(prefix)
        )

    stats = {
        "date": today_str(),
        "time": today_time_str(),
        "done_total": count_files(DONE_DIR),
        "email_done": count_files(DONE_DIR, "EMAIL_"),
        "approval_done": count_files(DONE_DIR, "APPROVAL_"),
        "needs_action": count_files(VAULT_PATH / "Needs_Action"),
        "pending_approvals": count_files(PENDING_APPROVAL_DIR),
        "plans_count": count_files(VAULT_PATH / "Plans"),
        "ralph_cycles": 0,
        "ralph_actions": 0,
        "ralph_errors": 0,
    }

    # Pull Ralph's operational stats if available
    if RALPH_STATE_FILE.exists():
        try:
            with open(RALPH_STATE_FILE, encoding="utf-8") as f:
                ralph_state = json.load(f)
            stats["ralph_cycles"] = ralph_state.get("total_cycles", 0)
            stats["ralph_actions"] = ralph_state.get("total_actions", 0)
            stats["ralph_errors"] = ralph_state.get("total_errors", 0)
        except (json.JSONDecodeError, KeyError):
            pass

    return stats


def load_templates() -> dict:
    """Load linkedin_templates.json from the MCP server directory."""
    if not TEMPLATES_FILE.exists():
        return {}
    with open(TEMPLATES_FILE, encoding="utf-8") as f:
        return json.load(f)


# ============================================================
# CONTENT GENERATION
# ============================================================

def select_content_type(history: dict) -> str:
    """
    Smart rotation: avoid repeating the same type within the last 3 posts.
    Falls back to round-robin if all types were used recently.
    """
    recent_types = [p["content_type"] for p in history["posts"][-3:]]
    for t in CONTENT_TYPES:
        if t not in recent_types:
            return t
    # All used recently — pick based on least recently used
    for t in CONTENT_TYPES:
        if t not in recent_types[-2:]:
            return t
    return CONTENT_TYPES[history["total_generated"] % len(CONTENT_TYPES)]


def generate_achievement_post(stats: dict, variant: int = 0) -> tuple[str, list]:
    """Data-driven weekly achievement post."""
    hashtags = ["#AIEmployee", "#Automation", "#ProductivityHacks", "#FutureOfWork", "#AI"]

    variants = [
        # Variant 0 — operational metrics focus
        f"""This week our AI Employee system ran autonomously — no micromanagement required.

Here's the actual activity log:

📬 Emails triaged: {stats['email_done']:,}
✅ Tasks completed: {stats['done_total']:,}
📋 Approvals managed: {stats['approval_done']:,}
🔄 Autonomous reasoning cycles: {stats['ralph_cycles']:,}
📂 Items still in queue: {stats['needs_action']:,}

Every task tracked. Every decision logged. Every action auditable.

This is what intelligent automation looks like when it's built right — not replacing judgment, just removing the routine.

What repetitive task is consuming the most of your team's time right now?""",

        # Variant 1 — impact / before-after framing
        f"""Real numbers from our AI Employee system this month:

Before automation:
→ Hours spent on email triage: too many to count
→ Tasks falling through the cracks: constantly
→ Approval bottlenecks: weekly frustration

After:
→ {stats['email_done']:,} emails processed autonomously
→ {stats['done_total']:,} tasks completed without human touch
→ {stats['approval_done']:,} decisions routed for human review

The AI doesn't make the decisions that matter.
It makes sure nothing important is ever missed.

What would your team do with that time back?""",
    ]

    return variants[variant % len(variants)], hashtags


def generate_thought_leadership_post(stats: dict, variant: int = 0) -> tuple[str, list]:
    """Rotating insights about AI automation and the future of work."""
    hashtags = ["#AI", "#Leadership", "#FutureOfWork", "#Innovation", "#Automation"]

    variants = [
        # Variant 0 — HITL insight
        """Most people get AI automation wrong.

They think the goal is to remove humans from the loop.

The real goal is the opposite: make sure humans are only in the loop for decisions that actually require human judgment.

Here's the framework we use:

✅ AI handles: triage, routing, categorisation, scheduling, drafting
✅ Human handles: approvals, relationships, strategy, exceptions

The result? Every decision a human makes is one that genuinely needed a human.

No more spending 40 minutes sorting emails.
No more losing track of approval requests.
No more status updates that could be automated.

HITL (Human-in-the-Loop) isn't a limitation on AI.
It's what makes AI trustworthy.

Where are you drawing the human/AI boundary in your workflow?""",

        # Variant 1 — OODA loop insight
        f"""The military uses the OODA loop for decision-making under pressure:
Observe → Orient → Decide → Act

We built our AI Employee the same way.

Every {stats['ralph_cycles']:,} autonomous cycles, the system:
🔍 Observes: scans all incoming tasks, emails, and approvals
🧠 Orients: scores by urgency, age, and impact
⚡ Decides: selects highest-value action within safety constraints
🎯 Acts: executes — then logs every detail
📝 Reflects: updates its state for the next cycle

The cycle runs every 60 minutes. Quiet hours respected. Safety gates enforced.

Most organisations' decision cycles take days.
Ours takes minutes.

What would it mean for your team to cut your decision cycle by 10x?""",

        # Variant 2 — automation tiers insight
        """There are 3 stages of workplace automation. Most teams are stuck at Stage 1.

Stage 1 — Tool automation
You use software to do specific tasks faster.
Email clients, project management tools, CRMs.
Result: marginal time savings.

Stage 2 — Workflow automation
You connect tools together with triggers and rules.
Zapier, Make, Power Automate.
Result: 20-40% overhead reduction.

Stage 3 — Intelligent automation
An AI Employee with reasoning, judgment, and memory.
Observes context. Prioritises autonomously. Escalates with precision.
Result: you stop managing routine and start directing strategy.

Most teams we talk to are deep in Stage 1, experimenting with Stage 2.

Stage 3 is not science fiction anymore.

Which stage is your team at?""",
    ]

    return variants[variant % len(variants)], hashtags


def generate_tip_post(stats: dict, variant: int = 0) -> tuple[str, list]:
    """Quick, practical AI automation tips."""
    hashtags = ["#AITips", "#Automation", "#Productivity", "#AI", "#WorkSmarter"]

    variants = [
        # Variant 0 — 3 tips format
        """3 things to do before automating any task:

1/ Map the exceptions, not just the happy path
Every process has edge cases. If the AI can't handle them gracefully, you haven't automated — you've just moved the problem.

2/ Design the audit trail first
If you can't explain every decision the automation made, you can't trust it. Log everything from day one.

3/ Start with observation, not action
Let the AI watch what happens for a cycle before it acts. The best automation is invisible because it's been calibrated to reality, not theory.

Most automation fails not because the technology is wrong — but because the process design was wrong.

Which of these is your biggest bottleneck?""",

        # Variant 1 — email triage tip
        """Your inbox is a to-do list managed by other people.

Here's how we fixed it with an AI Employee:

Step 1: Classify every incoming email automatically
→ Urgent (action needed today)
→ Normal (process within 48h)
→ FYI (read when relevant)
→ Promotional (archive)

Step 2: Route intelligently
→ Urgent → human review immediately
→ Normal → AI drafts response, human approves
→ FYI → filed and summarised weekly
→ Promotional → handled without human touch

Step 3: Never "check email" again
→ The system surfaces what you need, when you need it

Result: inbox zero isn't a discipline problem.
It's a systems problem.

What's your current email triage system?""",

        # Variant 2 — approval workflow tip
        """The approval bottleneck is the most expensive workflow problem most teams ignore.

Every time someone has to "wait for sign-off":
• Context is lost between request and decision
• Urgency compounds while the queue grows
• The decision-maker makes it cold, without context

Fix: design approvals like a well-structured brief.

When our AI Employee needs approval, it creates a file with:
📋 What action is requested (specific, not vague)
🎯 Why it's needed (context, not justification)
⚠️ Risk level and reversibility
⏱️ Expiry time (24h — stale approvals get re-requested)
✅ Exactly what happens when approved

The human reads, decides, moves a file.
The AI executes and logs the outcome.

Clear input → fast decision → auditable output.

How long does a typical approval take in your team?""",
    ]

    return variants[variant % len(variants)], hashtags


def generate_behind_scenes_post(stats: dict, variant: int = 0) -> tuple[str, list]:
    """Transparent, behind-the-scenes view of the AI Employee system."""
    hashtags = ["#BehindTheScenes", "#AI", "#AIEmployee", "#ClaudeAI", "#BuildInPublic"]

    variants = [
        # Variant 0 — live activity snapshot
        f"""Behind the scenes of our AI Employee system right now:

🔍 Observing: {stats['needs_action']:,} items in the active queue
🧠 Orienting: scoring each by urgency, age, and impact
⚡ Deciding: selecting the highest-value action within safety constraints
🎯 Acting: executing autonomously — every step logged
📝 Reflecting: updating state for the next cycle

This loop runs every 60 minutes.
Quiet hours (11 PM – 6 AM) respected automatically.
After 3 consecutive errors: loop pauses, human alerted.

Total cycles completed: {stats['ralph_cycles']:,}
Total actions taken: {stats['ralph_actions']:,}

No human needed for the routine.
Humans needed for the judgement calls.

Built with Claude Code + Model Context Protocol.

Ask me anything about how it works.""",

        # Variant 1 — the system architecture
        """What does an AI Employee actually look like under the hood?

Here's our stack, no filter:

📁 Vault (file system as the "brain")
→ Needs_Action/ — incoming tasks
→ Pending_Approval/ — decisions awaiting humans
→ Approved/ — actions cleared to execute
→ Done/ — full audit trail
→ Logs/ — structured activity history

🤖 Ralph (autonomous reasoning loop)
→ OODA cycle: Observe, Orient, Decide, Act, Reflect
→ Scores actions by urgency and impact
→ Executes via Claude Code CLI
→ Never acts without safety gates passing

🔧 MCP Servers (Claude's tools)
→ Email MCP: send emails via Gmail API
→ File Ops MCP: search, read, organise files
→ LinkedIn MCP: draft and post content (this post!)

🧠 Claude Code (the AI layer)
→ Reads context, applies judgment, takes action
→ Creates structured files, not freeform outputs

The whole thing is auditable, reversible, and designed around human oversight.

Questions?""",
    ]

    return variants[variant % len(variants)], hashtags


def generate_content(content_type: str, history: dict, stats: dict) -> dict:
    """
    Generate a post for the given content type.
    Uses variant index based on how many times this type has been used.
    """
    type_count = sum(1 for p in history["posts"] if p["content_type"] == content_type)

    generators = {
        "achievement": generate_achievement_post,
        "thought_leadership": generate_thought_leadership_post,
        "tip": generate_tip_post,
        "behind_the_scenes": generate_behind_scenes_post,
    }

    generator = generators.get(content_type, generate_achievement_post)
    content, hashtags = generator(stats, variant=type_count)

    post_id = generate_post_id()
    post_text = content + "\n\n" + " ".join(hashtags)

    return {
        "id": post_id,
        "content_type": content_type,
        "content": content,
        "hashtags": hashtags,
        "post_text": post_text,
        "visibility": "PUBLIC",
        "char_count": len(post_text),
        "created_at": now_iso(),
        "status": "draft",
        "approval_file": None,
        "plan_file": None,
        "posted_at": None,
        "post_url": None,
    }


# ============================================================
# QUALITY CHECKS
# ============================================================

def quality_check(post: dict) -> tuple[bool, list]:
    """
    Validate post quality. Returns (passed: bool, issues: list[str]).
    Hard failures block the post; warnings are logged but don't block.
    """
    issues = []
    text = post["post_text"]

    # Hard limit check
    if len(text) > CHAR_LIMIT_HARD:
        issues.append(f"FAIL: Exceeds hard limit ({len(text)}/{CHAR_LIMIT_HARD} chars)")
        return False, issues

    # Recommended length warning
    if len(text) > CHAR_LIMIT_RECOMMENDED:
        issues.append(f"WARN: Over recommended length ({len(text)}/{CHAR_LIMIT_RECOMMENDED} chars)")

    # Must have a hook (non-empty first line)
    lines = text.strip().split("\n")
    if not lines[0].strip():
        issues.append("FAIL: First line is empty — post needs a hook")
        return False, issues

    # Must have hashtags
    hashtag_count = len(post.get("hashtags", []))
    if hashtag_count == 0:
        issues.append("FAIL: No hashtags")
        return False, issues
    if hashtag_count > 10:
        issues.append(f"WARN: Too many hashtags ({hashtag_count}) — recommend 3-5")

    # Must end with engagement hook (question or CTA)
    content_lower = post["content"].lower()
    has_question = "?" in post["content"]
    has_cta = any(phrase in content_lower for phrase in [
        "comment", "share", "tag", "let me know", "dm me",
        "reach out", "connect", "follow", "what's your",
        "ask me", "drop", "reply",
    ])
    if not has_question and not has_cta:
        issues.append("WARN: Post lacks a question or CTA — engagement may suffer")

    # Professional tone check
    for pattern in UNPROFESSIONAL_PATTERNS:
        if re.search(pattern, text):
            issues.append(f"WARN: Possible unprofessional language: {pattern}")

    # Duplicate detection — check against last 6 posts
    # Use simple similarity: if >60% of hashtags match, flag it
    history = load_post_history()
    recent_posts = history["posts"][-6:]
    for recent in recent_posts:
        recent_tags = set(recent.get("hashtags", []))
        current_tags = set(post.get("hashtags", []))
        if recent_tags and current_tags:
            overlap = len(recent_tags & current_tags) / max(len(recent_tags), len(current_tags))
            if overlap > 0.8 and recent.get("content_type") == post.get("content_type"):
                issues.append(
                    f"WARN: Similar post already in history (id: {recent['id']}, "
                    f"type: {recent['content_type']}) — consider different variant"
                )
                break

    # Passes if no FAIL issues
    passed = not any(i.startswith("FAIL") for i in issues)
    return passed, issues


# ============================================================
# FILE CREATION
# ============================================================

def create_approval_file(post: dict, dry_run: bool = False) -> str:
    """
    Create a HITL approval request in Pending_Approval/.
    Follows HITL_APPROVAL_SKILL.md format with LINKEDIN_ prefix for easy detection.
    Returns the file path.
    """
    PENDING_APPROVAL_DIR.mkdir(parents=True, exist_ok=True)

    filename = f"LINKEDIN_POST_{post['id']}_{today_str()}.md"
    file_path = PENDING_APPROVAL_DIR / filename

    expires = (datetime.utcnow() + timedelta(hours=24)).strftime("%Y-%m-%dT%H:%M:%SZ")

    content = f"""---
type: linkedin_post_approval
action: publish_linkedin_post
post_id: {post['id']}
content_type: {post['content_type']}
created: {post['created_at']}
expires: {expires}
status: pending
risk_level: medium
requested_by: linkedin_auto_poster
simulation_mode: {str(SIMULATION_MODE).lower()}
---

# Approval Request: LinkedIn Post — {post['content_type'].replace('_', ' ').title()}

## Action Required
The AI Employee wants to publish the LinkedIn post below. Review content and approve or reject.

## Post Preview

> **Character count:** {post['char_count']} / 3000

---

{post['post_text']}

---

## Details
- **What will happen:** Post published to LinkedIn (visibility: {post['visibility']})
- **Content type:** {post['content_type'].replace('_', ' ').title()}
- **Hashtags:** {', '.join(post['hashtags'])}
- **Risk level:** Medium (public-facing content)
- **Reversible:** Yes (post can be deleted via LinkedIn)
- **Mode:** {"SIMULATION — no real post will be created" if SIMULATION_MODE else "LIVE — real LinkedIn API call"}

## Context
Generated automatically by `linkedin_auto_poster.py` as part of the {today_str()} M/W/F posting schedule.
Content type rotated to avoid repetition. Quality checks passed.

## To Approve
Move this file to **Approved/**
The AI Employee will {"log the simulated post action" if SIMULATION_MODE else "call the LinkedIn Posts API and publish"}, then move this file to Done/.

## To Reject
Move this file to **Rejected/**
The AI Employee will skip this post and log the rejection.

## Expiry
This request expires at **{expires}**.
If not actioned, it will be logged as timed out and a new request created next posting day.

---
*Generated by linkedin_auto_poster.py — {"SIMULATION" if SIMULATION_MODE else "LIVE"} mode*
*AI Employee Vault Gold v1.0*
"""

    if not dry_run:
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)

    return str(file_path)


def create_schedule_plan_file(posts_schedule: list, dry_run: bool = False) -> str:
    """
    Write a scheduling plan to Plans/ covering the next N posting slots.
    """
    plans_dir = VAULT_PATH / "Plans"
    plans_dir.mkdir(parents=True, exist_ok=True)

    filename = f"LINKEDIN_SCHEDULE_{today_str()}.md"
    file_path = plans_dir / filename

    rows = "\n".join(
        f"| {i+1} | {s['date']} ({s['weekday']}) | {s['time']} | {s['content_type'].replace('_', ' ').title()} | Pending |"
        for i, s in enumerate(posts_schedule)
    )

    content = f"""---
type: linkedin_post_schedule
created: {now_iso()}
status: active
posts_planned: {len(posts_schedule)}
simulation_mode: {str(SIMULATION_MODE).lower()}
---

# LinkedIn Post Schedule — Created {today_str()}

## Overview
Automated M/W/F posting schedule generated by `linkedin_auto_poster.py`.
Each slot will generate a post draft and route to Pending_Approval/ for HITL approval.

## Schedule

| # | Date | Time | Content Type | Status |
|---|------|------|--------------|--------|
{rows}

## Execution

Run on each posting day:
```bash
python linkedin_auto_poster.py --generate
```

Or let Ralph's loop handle it automatically via `--ralph-check`.

## Content Rotation
Posts rotate through: Achievement → Thought Leadership → Tip → Behind the Scenes → repeat.
The rotation avoids repeating the same type within 3 consecutive posts.

## Mode: {"SIMULATION" if SIMULATION_MODE else "LIVE"}
{"No real LinkedIn posts will be created. Approval files and logs are created for demonstration." if SIMULATION_MODE else "Live LinkedIn API calls will be made after human approval."}

---
*Generated by linkedin_auto_poster.py — AI Employee Vault Gold v1.0*
"""

    if not dry_run:
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)

    return str(file_path)


# ============================================================
# SCHEDULE CALCULATION
# ============================================================

def get_next_posting_slots(count: int = 6) -> list:
    """
    Return the next `count` M/W/F 10 AM slots from today.
    Each slot: {"date": "YYYY-MM-DD", "weekday": "Monday", "time": "10:00", "datetime": datetime, "content_type": str}
    """
    history = load_post_history()
    slots = []
    check_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    type_index = history["total_generated"] % len(CONTENT_TYPES)

    while len(slots) < count:
        check_date += timedelta(days=1)
        if check_date.weekday() in POSTING_DAYS:
            content_type = CONTENT_TYPES[type_index % len(CONTENT_TYPES)]
            slots.append({
                "date": check_date.strftime("%Y-%m-%d"),
                "weekday": POSTING_DAYS[check_date.weekday()],
                "time": f"{POSTING_HOUR:02d}:00",
                "datetime": check_date.replace(hour=POSTING_HOUR),
                "content_type": content_type,
            })
            type_index += 1

    return slots


def is_posting_day() -> bool:
    """True if today is Monday, Wednesday, or Friday."""
    return datetime.now().weekday() in POSTING_DAYS


def is_posting_window() -> bool:
    """True if current time is within ±90 minutes of POSTING_HOUR."""
    now = datetime.now()
    target = now.replace(hour=POSTING_HOUR, minute=0, second=0)
    delta = abs((now - target).total_seconds()) / 60
    return delta <= POSTING_WINDOW_MINUTES


def already_posted_today(history: dict) -> bool:
    """True if a post was already generated today."""
    return any(
        p["created_at"].startswith(today_str())
        for p in history["posts"]
    )


def posts_this_week(history: dict) -> int:
    """Count posts generated in the current ISO week."""
    week_start = (datetime.now() - timedelta(days=datetime.now().weekday())).date()
    return sum(
        1 for p in history["posts"]
        if datetime.fromisoformat(p["created_at"].rstrip("Z")).date() >= week_start
    )


# ============================================================
# MAIN WORKFLOWS
# ============================================================

def run_generate(dry_run: bool = False) -> int:
    """
    Generate a LinkedIn post draft and create an approval request.
    Returns 0 on success, 1 on failure.
    """
    print_section("LinkedIn Auto-Poster — Generate")
    print_info("Mode:", "SIMULATION (no real API calls)" if SIMULATION_MODE else "LIVE")
    print_info("Dry run:", "YES — no files will be written" if dry_run else "NO")

    history = load_post_history()
    stats = load_vault_stats()

    # Check weekly cap
    week_count = posts_this_week(history)
    if week_count >= MAX_POSTS_PER_WEEK and not dry_run:
        print(f"\n  Weekly cap reached ({week_count}/{MAX_POSTS_PER_WEEK} posts).")
        print("  No post generated.")
        return 0

    # Select content type via smart rotation
    content_type = select_content_type(history)
    print_info("Content type:", content_type.replace("_", " ").title())
    print_info("Vault stats:", f"{stats['done_total']} done, {stats['needs_action']} pending")
    print_info("Ralph cycles:", stats["ralph_cycles"])

    # Generate content
    post = generate_content(content_type, history, stats)
    print_info("Post ID:", post["id"])
    print_info("Char count:", f"{post['char_count']} / {CHAR_LIMIT_HARD}")

    # Quality check
    passed, issues = quality_check(post)
    if issues:
        print("\n  Quality check results:")
        for issue in issues:
            print(f"    {'❌' if issue.startswith('FAIL') else '⚠️ '} {issue}")

    if not passed:
        print("\n  Post failed quality check. Aborting.")
        log_action(f"Quality check failed for {content_type} post {post['id']}", status="failed")
        return 1

    # Preview
    print("\n  --- POST PREVIEW ---")
    print()
    for line in post["post_text"].split("\n"):
        print(f"  {line}")
    print("\n  --- END PREVIEW ---")

    if dry_run:
        print("\n  [DRY RUN] No files written.")
        return 0

    # Create approval file
    approval_path = create_approval_file(post)
    post["status"] = "pending_approval"
    post["approval_file"] = str(Path(approval_path).relative_to(VAULT_PATH))

    # Update history
    history["posts"].append(post)
    history["total_generated"] += 1
    save_post_history(history)

    # Log action
    log_action(
        f"Generated {content_type} post {post['id']}, approval requested",
        action_type="linkedin_post_generated",
        status="pending_approval",
    )

    print(f"\n  ✅ Post draft created.")
    print(f"  Approval file: {post['approval_file']}")
    print(f"  Action: move to Approved/ to confirm, Rejected/ to cancel.")
    return 0


def run_schedule(dry_run: bool = False) -> int:
    """
    Generate a 2-week posting schedule (6 slots) and save as a plan file.
    """
    print_section("LinkedIn Auto-Poster — Schedule")

    slots = get_next_posting_slots(count=6)

    print(f"\n  Next {len(slots)} posting slots (M/W/F at {POSTING_HOUR}:00):\n")
    for slot in slots:
        print(f"  📅 {slot['date']} ({slot['weekday']}) — {slot['content_type'].replace('_', ' ').title()}")

    if dry_run:
        print("\n  [DRY RUN] No plan file written.")
        return 0

    plan_path = create_schedule_plan_file(slots)
    rel_path = Path(plan_path).relative_to(VAULT_PATH)
    log_action(f"Schedule plan created: {rel_path}", action_type="linkedin_schedule_created")

    print(f"\n  ✅ Schedule saved: {rel_path}")
    return 0


def run_check_approved() -> int:
    """
    Detect LINKEDIN_POST_*.md files in Approved/, execute (or simulate),
    then move to Done/ and update history.
    """
    print_section("LinkedIn Auto-Poster — Check Approved")

    if not APPROVED_DIR.exists():
        print("  Approved/ directory does not exist. Nothing to process.")
        return 0

    approved_posts = list(APPROVED_DIR.glob("LINKEDIN_POST_*.md"))
    rejected_posts = list(REJECTED_DIR.glob("LINKEDIN_POST_*.md")) if REJECTED_DIR.exists() else []

    if not approved_posts and not rejected_posts:
        print("  No pending LinkedIn decisions found.")
        return 0

    history = load_post_history()
    processed = 0

    # Process approvals
    for approval_file in approved_posts:
        post_id = approval_file.stem.split("_")[2] if len(approval_file.stem.split("_")) > 2 else "UNKNOWN"
        print(f"\n  ✅ APPROVED: {approval_file.name}")

        # Find post in history
        post_record = next((p for p in history["posts"] if p["id"] == post_id), None)

        if SIMULATION_MODE:
            print(f"     [SIMULATION] Post {post_id} would be published to LinkedIn.")
            print(f"     Content type: {post_record['content_type'] if post_record else 'unknown'}")
            sim_url = f"https://www.linkedin.com/feed/update/urn:li:share:SIM_{post_id}/"
            print(f"     Simulated URL: {sim_url}")

            if post_record:
                post_record["status"] = "posted_simulated"
                post_record["posted_at"] = now_iso()
                post_record["post_url"] = sim_url
                history["total_posted"] += 1

            log_action(
                f"SIMULATED: post {post_id} approved and published (simulation)",
                action_type="linkedin_post_published",
                status="simulated",
            )
        else:
            # PRODUCTION: LinkedIn API call would go here
            # Requires LINKEDIN_ACCESS_TOKEN env var set
            print(f"     [LIVE] Would call LinkedIn Posts API for {post_id}")
            if post_record:
                post_record["status"] = "posted"
                post_record["posted_at"] = now_iso()
                history["total_posted"] += 1

        # Move to Done/
        DONE_DIR.mkdir(parents=True, exist_ok=True)
        done_path = DONE_DIR / approval_file.name
        approval_file.rename(done_path)
        print(f"     Moved to Done/: {approval_file.name}")
        processed += 1

    # Process rejections
    for rejection_file in rejected_posts:
        post_id = rejection_file.stem.split("_")[2] if len(rejection_file.stem.split("_")) > 2 else "UNKNOWN"
        print(f"\n  ❌ REJECTED: {rejection_file.name}")

        post_record = next((p for p in history["posts"] if p["id"] == post_id), None)
        if post_record:
            post_record["status"] = "rejected"
            history["total_rejected"] += 1

        log_action(
            f"Post {post_id} rejected by human", action_type="linkedin_post_rejected"
        )

        DONE_DIR.mkdir(parents=True, exist_ok=True)
        done_path = DONE_DIR / rejection_file.name
        rejection_file.rename(done_path)
        print(f"     Moved to Done/: {rejection_file.name}")
        processed += 1

    if processed > 0:
        save_post_history(history)

    print(f"\n  Processed {processed} decision(s).")
    return 0


def run_ralph_check(dry_run: bool = False) -> int:
    """
    Smart decision point for Ralph's loop:
    1. Check if there are any approved/rejected LinkedIn posts to process.
    2. If today is a posting day and within the time window, generate a post.
    This mode is designed to be called every cycle — it is idempotent.
    """
    print_section("LinkedIn Auto-Poster — Ralph Check")

    # Step 1: Always process any pending approvals first
    approved_count = len(list(APPROVED_DIR.glob("LINKEDIN_POST_*.md"))) if APPROVED_DIR.exists() else 0
    rejected_count = len(list(REJECTED_DIR.glob("LINKEDIN_POST_*.md"))) if REJECTED_DIR.exists() else 0

    if approved_count + rejected_count > 0:
        print(f"  Found {approved_count} approved, {rejected_count} rejected. Processing...")
        return run_check_approved()

    # Step 2: Check if it's time to generate a new post
    history = load_post_history()
    today_is_posting_day = is_posting_day()
    in_window = is_posting_window()
    posted_today = already_posted_today(history)
    week_count = posts_this_week(history)

    print_info("Today is posting day:", "Yes" if today_is_posting_day else "No")
    print_info("In posting window:", "Yes" if in_window else "No")
    print_info("Already posted today:", "Yes" if posted_today else "No")
    print_info("Posts this week:", f"{week_count} / {MAX_POSTS_PER_WEEK}")

    if today_is_posting_day and in_window and not posted_today and week_count < MAX_POSTS_PER_WEEK:
        print("\n  ✅ Conditions met — generating post now.")
        return run_generate(dry_run=dry_run)
    else:
        reasons = []
        if not today_is_posting_day:
            next_slots = get_next_posting_slots(1)
            reasons.append(f"not a posting day (next: {next_slots[0]['date']} {next_slots[0]['weekday']})")
        if not in_window:
            reasons.append(f"outside posting window ({POSTING_HOUR}:00 ± {POSTING_WINDOW_MINUTES}min)")
        if posted_today:
            reasons.append("already posted today")
        if week_count >= MAX_POSTS_PER_WEEK:
            reasons.append(f"weekly cap reached ({week_count}/{MAX_POSTS_PER_WEEK})")
        print(f"\n  No action needed: {', '.join(reasons)}.")
        return 0


def run_status() -> int:
    """Display queue, history, and next posting schedule."""
    print_section("LinkedIn Auto-Poster — Status")

    history = load_post_history()
    stats = load_vault_stats()

    print_info("Mode:", "SIMULATION" if SIMULATION_MODE else "LIVE")
    print_info("Total generated:", history["total_generated"])
    print_info("Total approved/posted:", history["total_posted"])
    print_info("Total rejected:", history["total_rejected"])
    print_info("Posts this week:", posts_this_week(history))
    print_info("Today is posting day:", "Yes" if is_posting_day() else "No")
    print_info("In posting window:", "Yes" if is_posting_window() else "No")

    # Pending approval files
    pending = list(PENDING_APPROVAL_DIR.glob("LINKEDIN_POST_*.md")) if PENDING_APPROVAL_DIR.exists() else []
    print_info("Pending approvals:", len(pending))
    for f in pending:
        print(f"    → {f.name}")

    # Approved, waiting to execute
    approved = list(APPROVED_DIR.glob("LINKEDIN_POST_*.md")) if APPROVED_DIR.exists() else []
    print_info("Approved (not yet executed):", len(approved))
    for f in approved:
        print(f"    → {f.name}")

    # Recent history
    recent = history["posts"][-5:]
    if recent:
        print("\n  Recent Posts:")
        for p in reversed(recent):
            date = p["created_at"][:10]
            print(f"    [{date}] {p['content_type'].replace('_', ' ').title()} — {p['status']} (id: {p['id']})")

    # Next slots
    next_slots = get_next_posting_slots(3)
    print("\n  Upcoming Slots:")
    for slot in next_slots:
        print(f"    📅 {slot['date']} ({slot['weekday']}) at {slot['time']} — {slot['content_type'].replace('_', ' ').title()}")

    return 0


# ============================================================
# CLI ENTRY POINT
# ============================================================

def main():
    parser = argparse.ArgumentParser(
        description="LinkedIn Auto-Poster — AI Employee Vault Gold Tier",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python linkedin_auto_poster.py --generate
  python linkedin_auto_poster.py --generate --dry-run
  python linkedin_auto_poster.py --schedule
  python linkedin_auto_poster.py --check-approved
  python linkedin_auto_poster.py --status
  python linkedin_auto_poster.py --ralph-check
        """,
    )
    parser.add_argument("--generate", action="store_true",
                        help="Generate today's post and create approval request")
    parser.add_argument("--schedule", action="store_true",
                        help="Generate 2-week M/W/F posting schedule")
    parser.add_argument("--check-approved", action="store_true",
                        help="Execute any approved LinkedIn posts")
    parser.add_argument("--status", action="store_true",
                        help="Show posting queue, history, and next slots")
    parser.add_argument("--ralph-check", action="store_true",
                        help="Smart mode for Ralph's loop — decides action automatically")
    parser.add_argument("--dry-run", action="store_true",
                        help="Preview actions without writing any files")

    args = parser.parse_args()

    if args.generate:
        sys.exit(run_generate(dry_run=args.dry_run))
    elif args.schedule:
        sys.exit(run_schedule(dry_run=args.dry_run))
    elif args.check_approved:
        sys.exit(run_check_approved())
    elif args.status:
        sys.exit(run_status())
    elif args.ralph_check:
        sys.exit(run_ralph_check(dry_run=args.dry_run))
    else:
        parser.print_help()
        print("\n  No mode specified. Use --status to see current state.")
        sys.exit(0)


if __name__ == "__main__":
    main()
