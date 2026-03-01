#!/usr/bin/env python3
"""
AI Employee Vault - Social Media Auto-Poster v3.0
==================================================
Gold Tier: Autonomous multi-platform content generation and posting workflow.

Generates professional posts for LinkedIn, Facebook, Twitter, and Instagram
from vault activity data, creates HITL approval requests, and executes
approved posts (simulated or live). Designed for Ralph's OODA loop OR
standalone use.

Usage:
  python social_media_auto_poster.py --generate [--platform linkedin|facebook|twitter|instagram|all]
  python social_media_auto_poster.py --schedule [--platform linkedin]
  python social_media_auto_poster.py --check-approved
  python social_media_auto_poster.py --status
  python social_media_auto_poster.py --ralph-check
  python social_media_auto_poster.py --cross-post --content "Your message here"
  python social_media_auto_poster.py --dry-run [--platform all]
"""

import argparse
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

# Simulation flags — match the flags in mcp_servers/social_media_mcp/index.js
SIMULATE_LINKEDIN  = True
SIMULATE_FACEBOOK  = True
SIMULATE_TWITTER   = True
SIMULATE_INSTAGRAM = True

# Posting schedules
POSTING_DAYS   = {0: "Monday", 2: "Wednesday", 4: "Friday"}  # Mon/Wed/Fri
POSTING_HOUR   = 10
POSTING_WINDOW_MINUTES = 90  # +-90 min around 10 AM

# Platform limits
LINKEDIN_CHAR_LIMIT   = 3000
LINKEDIN_CHAR_REC     = 1300
TWITTER_CHAR_LIMIT    = 280
INSTAGRAM_CHAR_LIMIT  = 2200
INSTAGRAM_HASHTAG_MAX = 30

MAX_POSTS_PER_WEEK = 3

# Content rotation order
CONTENT_TYPES = ["achievement", "thought_leadership", "tip", "behind_the_scenes"]

# File paths
HISTORY_FILE          = VAULT_PATH / "social_media_post_history.json"
TEMPLATES_FILE        = VAULT_PATH / "mcp_servers" / "social_media_mcp" / "social_media_templates.json"
RALPH_STATE_FILE      = VAULT_PATH / "Logs" / "ralph" / "ralph_state.json"
PENDING_APPROVAL_DIR  = VAULT_PATH / "Pending_Approval"
APPROVED_DIR          = VAULT_PATH / "Approved"
REJECTED_DIR          = VAULT_PATH / "Rejected"
DONE_DIR              = VAULT_PATH / "Done"
LOGS_DIR              = VAULT_PATH / "Logs"

# Twitter hashtag limits
TWITTER_HASHTAG_REC = 2

# Quality — words that signal unprofessional tone
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
    return format(random.randint(0, 0xFFFFFFFF), "08X")

def log_action(message: str, platform: str = "social", status: str = "success") -> None:
    log_file = LOGS_DIR / f"{today_str()}.md"
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    entry = f"""
---
timestamp: {now_iso()}
action_type: social_media_post
actor: social_media_auto_poster
platform: {platform}
status: {status}
---

## Action: Social Media Auto-Poster — {message}

**Details:**
- Script: social_media_auto_poster.py
- Platform: {platform}
- Mode: {"SIMULATION" if SIMULATE_LINKEDIN else "LIVE"}
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
    print(f"  {label:<35} {value}")

# ============================================================
# DATA LOADING
# ============================================================

def load_post_history() -> dict:
    if not HISTORY_FILE.exists():
        return {
            "version": "2.0",
            "created": now_iso(),
            "last_updated": now_iso(),
            "platforms": {
                "linkedin":  {"total_generated": 0, "total_approved": 0, "total_rejected": 0, "total_posted": 0},
                "facebook":  {"total_generated": 0, "total_approved": 0, "total_rejected": 0, "total_posted": 0},
                "twitter":   {"total_generated": 0, "total_approved": 0, "total_rejected": 0, "total_posted": 0},
                "instagram": {"total_generated": 0, "total_approved": 0, "total_rejected": 0, "total_posted": 0},
            },
            "posts": [],
        }
    with open(HISTORY_FILE, encoding="utf-8") as f:
        return json.load(f)

def save_post_history(history: dict) -> None:
    history["last_updated"] = now_iso()
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(history, f, indent=2)

def load_vault_stats() -> dict:
    def count_files(directory: Path, prefix: str = "") -> int:
        if not directory.exists():
            return 0
        return sum(1 for f in directory.iterdir() if f.is_file() and f.name.startswith(prefix))

    stats = {
        "date": today_str(),
        "time": today_time_str(),
        "done_total":       count_files(DONE_DIR),
        "email_done":       count_files(DONE_DIR, "EMAIL_"),
        "approval_done":    count_files(DONE_DIR, "APPROVAL_"),
        "needs_action":     count_files(VAULT_PATH / "Needs_Action"),
        "pending_approvals": count_files(PENDING_APPROVAL_DIR),
        "plans_count":      count_files(VAULT_PATH / "Plans"),
        "ralph_cycles":     0,
        "ralph_actions":    0,
        "ralph_errors":     0,
    }
    if RALPH_STATE_FILE.exists():
        try:
            with open(RALPH_STATE_FILE, encoding="utf-8") as f:
                rs = json.load(f)
            stats["ralph_cycles"]  = rs.get("cycle_count", rs.get("total_cycles", 0))
            stats["ralph_actions"] = rs.get("total_items_processed", rs.get("total_actions", 0))
            stats["ralph_errors"]  = rs.get("consecutive_errors", rs.get("total_errors", 0))
        except (json.JSONDecodeError, KeyError):
            pass
    return stats

def load_templates() -> dict:
    if not TEMPLATES_FILE.exists():
        return {}
    with open(TEMPLATES_FILE, encoding="utf-8") as f:
        return json.load(f)

# ============================================================
# CONTENT GENERATION — LINKEDIN
# ============================================================

def select_content_type(history: dict) -> str:
    recent = [p["content_type"] for p in history["posts"][-3:]]
    for t in CONTENT_TYPES:
        if t not in recent:
            return t
    for t in CONTENT_TYPES:
        if t not in recent[-2:]:
            return t
    return CONTENT_TYPES[len(history["posts"]) % len(CONTENT_TYPES)]

def _achievement_text(stats: dict, variant: int) -> tuple:
    hashtags = ["#AIEmployee", "#Automation", "#ProductivityHacks", "#FutureOfWork", "#AI"]
    variants = [
        f"""This week our AI Employee system ran autonomously — no micromanagement required.

Here's the actual activity log:

Emails triaged: {stats['email_done']:,}
Tasks completed: {stats['done_total']:,}
Approvals managed: {stats['approval_done']:,}
Autonomous reasoning cycles: {stats['ralph_cycles']:,}
Items still in queue: {stats['needs_action']:,}

Every task tracked. Every decision logged. Every action auditable.

This is what intelligent automation looks like when it's built right — not replacing judgment, just removing the routine.

What repetitive task is consuming the most of your team's time right now?""",
        f"""Real numbers from our AI Employee system this month:

Before automation:
-> Hours spent on email triage: too many to count
-> Tasks falling through the cracks: constantly

After:
-> {stats['email_done']:,} emails processed autonomously
-> {stats['done_total']:,} tasks completed without human touch
-> {stats['approval_done']:,} decisions routed for human review

The AI doesn't make the decisions that matter.
It makes sure nothing important is ever missed.

What would your team do with that time back?""",
    ]
    return variants[variant % len(variants)], hashtags

def _thought_leadership_text(stats: dict, variant: int) -> tuple:
    hashtags = ["#AI", "#Leadership", "#FutureOfWork", "#Innovation", "#Automation"]
    variants = [
        """Most people get AI automation wrong.

They think the goal is to remove humans from the loop.

The real goal is the opposite: make sure humans are only in the loop for decisions that actually require human judgment.

Here's the framework we use:

AI handles: triage, routing, categorisation, scheduling, drafting
Human handles: approvals, relationships, strategy, exceptions

The result? Every decision a human makes is one that genuinely needed a human.

HITL (Human-in-the-Loop) isn't a limitation on AI.
It's what makes AI trustworthy.

Where are you drawing the human/AI boundary in your workflow?""",
        f"""The military uses the OODA loop for decision-making under pressure:
Observe -> Orient -> Decide -> Act

We built our AI Employee the same way.

Every {stats['ralph_cycles']:,} autonomous cycles, the system:
Observes: scans all incoming tasks, emails, and approvals
Orients: scores by urgency, age, and impact
Decides: selects highest-value action within safety constraints
Acts: executes — then logs every detail
Reflects: updates its state for the next cycle

The cycle runs every 60 minutes. Quiet hours respected. Safety gates enforced.

What would it mean for your team to cut your decision cycle by 10x?""",
    ]
    return variants[variant % len(variants)], hashtags

def _tip_text(stats: dict, variant: int) -> tuple:
    hashtags = ["#AITips", "#Automation", "#Productivity", "#AI", "#WorkSmarter"]
    variants = [
        """3 things to do before automating any task:

1/ Map the exceptions, not just the happy path
Every process has edge cases. If the AI can't handle them gracefully, you haven't automated — you've just moved the problem.

2/ Design the audit trail first
If you can't explain every decision the automation made, you can't trust it. Log everything from day one.

3/ Start with observation, not action
Let the AI watch what happens for a cycle before it acts. The best automation is invisible because it's been calibrated to reality, not theory.

Which of these is your biggest bottleneck?""",
        """Your inbox is a to-do list managed by other people.

Here's how we fixed it with an AI Employee:

Step 1: Classify every incoming email automatically
-> Urgent (action needed today)
-> Normal (process within 48h)
-> FYI (read when relevant)
-> Promotional (archive)

Step 2: Route intelligently — AI drafts, human approves
Step 3: Never "check email" again — system surfaces what you need

Result: inbox zero isn't a discipline problem. It's a systems problem.

What's your current email triage system?""",
    ]
    return variants[variant % len(variants)], hashtags

def _behind_scenes_text(stats: dict, variant: int) -> tuple:
    hashtags = ["#BehindTheScenes", "#AI", "#AIEmployee", "#ClaudeAI", "#BuildInPublic"]
    variants = [
        f"""Behind the scenes of our AI Employee system right now:

Observing: {stats['needs_action']:,} items in the active queue
Orienting: scoring each by urgency, age, and impact
Deciding: selecting the highest-value action within safety constraints
Acting: executing autonomously — every step logged
Reflecting: updating state for the next cycle

Total cycles completed: {stats['ralph_cycles']:,}
Quiet hours (11 PM - 6 AM) respected automatically.

Built with Claude Code + Model Context Protocol.

Ask me anything about how it works.""",
        """What does an AI Employee actually look like under the hood?

Here's our stack, no filter:

Vault (file system as the "brain")
-> Needs_Action/ — incoming tasks
-> Pending_Approval/ — decisions awaiting humans
-> Done/ — full audit trail

Ralph (autonomous reasoning loop)
-> OODA cycle: Observe, Orient, Decide, Act, Reflect
-> Never acts without safety gates passing

MCP Servers (Claude's tools)
-> Email MCP: send emails via Gmail API
-> File Ops MCP: search, read, organise files
-> Social Media MCP: draft posts for all 3 platforms (this post!)

The whole thing is auditable, reversible, and designed around human oversight.

Questions?""",
    ]
    return variants[variant % len(variants)], hashtags

def generate_linkedin_content(content_type: str, history: dict, stats: dict) -> dict:
    type_count = sum(1 for p in history["posts"] if p.get("content_type") == content_type and p.get("platform") == "linkedin")
    generators = {
        "achievement":        _achievement_text,
        "thought_leadership": _thought_leadership_text,
        "tip":                _tip_text,
        "behind_the_scenes":  _behind_scenes_text,
    }
    gen = generators.get(content_type, _achievement_text)
    content, hashtags = gen(stats, variant=type_count)
    post_text = content + "\n\n" + " ".join(hashtags)
    post_id = generate_post_id()
    return {
        "id": post_id,
        "platform": "linkedin",
        "content_type": content_type,
        "content": content,
        "hashtags": hashtags,
        "post_text": post_text,
        "visibility": "PUBLIC",
        "char_count": len(post_text),
        "created_at": now_iso(),
        "status": "draft",
        "approval_file": None,
    }

# ============================================================
# CONTENT GENERATION — TWITTER
# ============================================================

def split_for_twitter(text: str, hashtags: list = None) -> list:
    """Split text into 280-char thread chunks. Returns list of tweet strings."""
    hashtags = hashtags or []
    MARKER = 8  # space for " [N/N]"
    effective_max = TWITTER_CHAR_LIMIT - MARKER

    tags = " ".join(h if h.startswith("#") else f"#{h}" for h in hashtags[:TWITTER_HASHTAG_REC])
    full = text.strip()
    with_tags = f"{full}\n\n{tags}" if tags else full

    if len(with_tags) <= TWITTER_CHAR_LIMIT:
        return [with_tags]

    # Thread split
    words = full.split()
    chunks, current = [], ""
    for word in words:
        cand = f"{current} {word}".strip()
        if len(cand) <= effective_max:
            current = cand
        else:
            if current:
                chunks.append(current)
            current = word
    if current:
        chunks.append(current)

    if len(chunks) > 1:
        chunks = [f"{c} [{i+1}/{len(chunks)}]" for i, c in enumerate(chunks)]

    # Add tags to last chunk if it fits
    if tags and len(f"{chunks[-1]}\n{tags}") <= TWITTER_CHAR_LIMIT:
        chunks[-1] = f"{chunks[-1]}\n{tags}"

    return chunks

def generate_twitter_content(content_type: str, history: dict, stats: dict) -> dict:
    """Generate a Twitter-optimised version of the content (shorter, punchier)."""
    twitter_content = {
        "achievement": (
            f"Week in numbers for our AI Employee:\n\n"
            f"{stats['email_done']:,} emails triaged\n"
            f"{stats['done_total']:,} tasks completed\n"
            f"{stats['ralph_cycles']:,} autonomous reasoning cycles\n\n"
            f"Zero micromanagement. This is automation done right.",
            ["#AI", "#Automation"]
        ),
        "thought_leadership": (
            "Hot take: the most important AI skill isn't prompting.\n\n"
            "It's knowing what NOT to automate.\n\n"
            "Some decisions need a human. Full stop.",
            ["#AI", "#Leadership"]
        ),
        "tip": (
            "Quick tip for building with AI:\n\n"
            "Don't start with 'what can AI do?'\n\n"
            "Start with 'what takes 20% of my time and requires 0% of my judgment?'\n\n"
            "That's your first automation. Go.",
            ["#Productivity", "#AI"]
        ),
        "behind_the_scenes": (
            f"Behind the scenes: our AI Employee just completed cycle #{stats['ralph_cycles']:,}.\n\n"
            f"Processed {stats['done_total']:,} tasks. Zero micromanagement.\n\n"
            f"Built on OODA loop + Claude Code + plain markdown files.",
            ["#BuildInPublic", "#AI"]
        ),
    }

    content, hashtags = twitter_content.get(content_type, twitter_content["achievement"])
    thread = split_for_twitter(content, hashtags)
    post_id = generate_post_id()

    return {
        "id": post_id,
        "platform": "twitter",
        "content_type": content_type,
        "content": content,
        "hashtags": hashtags,
        "thread": thread,
        "is_thread": len(thread) > 1,
        "tweet_count": len(thread),
        "created_at": now_iso(),
        "status": "draft",
        "approval_file": None,
    }

# ============================================================
# CONTENT GENERATION — INSTAGRAM
# ============================================================

def generate_instagram_content(content_type: str, history: dict, stats: dict) -> dict:
    """Generate an Instagram-optimised caption (visual-first, hashtag-heavy)."""
    hashtags_base = ["#ai", "#artificialintelligence", "#automation", "#productivity",
                     "#tech", "#innovation", "#startup", "#entrepreneurship",
                     "#buildinpublic", "#developer", "#softwareengineering",
                     "#machinelearning", "#futureofwork", "#remotework",
                     "#worksmarter", "#digital", "#technology", "#business",
                     "#leadership", "#coding"]

    captions = {
        "achievement": (
            f"Week in numbers for our AI Employee system.\n\n"
            f"{stats['email_done']:,} emails triaged automatically.\n"
            f"{stats['done_total']:,} tasks completed.\n"
            f"{stats['ralph_cycles']:,} autonomous reasoning cycles.\n\n"
            f"The future of work isn't about replacing people.\n"
            f"It's about removing the friction that keeps smart people from doing smart work.\n\n"
            f"What's your automation win this week? Tell me below."
        ),
        "thought_leadership": (
            "The AI lesson nobody talks about:\n\n"
            "The tool is never the problem.\n"
            "The workflow around the tool is.\n\n"
            "Before you add AI, fix the process. Then automate it.\n\n"
            "What's one thing AI has actually helped you do better? "
            "Tell me in the comments."
        ),
        "tip": (
            "AI automation tip that actually works:\n\n"
            "Before you automate anything, ask:\n"
            "'Does this decision need human judgment?'\n\n"
            "If YES -> keep human in the loop\n"
            "If NO -> automate it\n\n"
            "That simple filter saves you from every AI horror story you've heard.\n\n"
            "Save this for your next automation project."
        ),
        "behind_the_scenes": (
            "Behind the curtain: what our AI Employee actually runs on.\n\n"
            "Not a fancy cloud platform.\n"
            "Not an expensive enterprise tool.\n\n"
            "A folder. A loop. And clear rules about when humans stay in control.\n\n"
            "The best systems are the ones you can explain in 30 seconds.\n\n"
            "What's the simplest tool in your stack that does the most work?"
        ),
    }

    caption = captions.get(content_type, captions["achievement"])
    post_id = generate_post_id()

    return {
        "id": post_id,
        "platform": "instagram",
        "content_type": content_type,
        "caption": caption,
        "hashtags": hashtags_base[:25],
        "post_type": "feed",
        "image_url": "",  # Must be provided before going live
        "char_count": len(caption),
        "created_at": now_iso(),
        "status": "draft",
        "approval_file": None,
    }

# ============================================================
# CONTENT GENERATION — FACEBOOK
# ============================================================

def generate_facebook_content(content_type: str, history: dict, stats: dict) -> dict:
    """Generate a Facebook-optimised post — casual, short, ends with a direct question."""
    facebook_posts = {
        "achievement": (
            f"Our AI Employee wrapped up another autonomous week.\n\n"
            f"{stats['email_done']:,} emails handled. {stats['done_total']:,} tasks completed. "
            f"{stats['ralph_cycles']:,} reasoning cycles. Zero micromanagement.\n\n"
            f"This is what thoughtful automation actually looks like in practice — "
            f"every decision logged, every action auditable, humans in the loop for anything that matters.\n\n"
            f"What's one repetitive task you wish you could hand off to an AI right now?",
            ["#AI", "#Automation"]
        ),
        "thought_leadership": (
            "Unpopular opinion: most AI tools fail not because of the AI — "
            "but because of the broken workflow around it.\n\n"
            "You can't bolt AI onto a broken process and expect magic. "
            "The AI just automates the chaos.\n\n"
            "Fix the process first. Then automate.\n\n"
            "What's one workflow you'd redesign if you started from scratch today?",
            ["#AI", "#Leadership"]
        ),
        "tip": (
            "Quick framework for AI automation that actually works:\n\n"
            "Ask yourself: does this decision need human judgment?\n\n"
            "YES → keep a human in the loop\n"
            "NO → automate it\n\n"
            "That one filter saves you from every AI horror story you've heard.\n\n"
            "What are you still doing manually that passes the 'no judgment needed' test?",
            ["#Productivity", "#AI"]
        ),
        "behind_the_scenes": (
            f"Behind the scenes of our AI Employee system:\n\n"
            f"It runs on a folder structure, a reasoning loop, and clear rules about "
            f"when humans stay in control. No fancy cloud platform. No expensive enterprise software.\n\n"
            f"Completed cycle #{stats['ralph_cycles']:,} this week. "
            f"{stats['needs_action']:,} items still in the active queue.\n\n"
            f"The best systems are the ones simple enough to explain in 30 seconds. "
            f"What's the simplest tool in your stack that does the most work?",
            ["#BuildInPublic", "#AI"]
        ),
    }

    content, hashtags = facebook_posts.get(content_type, facebook_posts["achievement"])
    post_id = generate_post_id()
    tag_str = " ".join(h if h.startswith("#") else f"#{h}" for h in hashtags)
    full_text = f"{content}\n\n{tag_str}"

    return {
        "id": post_id,
        "platform": "facebook",
        "content_type": content_type,
        "content": content,
        "hashtags": hashtags,
        "post_text": full_text,
        "target_type": "profile",  # "profile" or "page"
        "char_count": len(full_text),
        "created_at": now_iso(),
        "status": "draft",
        "approval_file": None,
    }


# ============================================================
# QUALITY CHECKS
# ============================================================

def quality_check_linkedin(post: dict) -> tuple:
    issues = []
    text = post["post_text"]
    if len(text) > LINKEDIN_CHAR_LIMIT:
        return False, [f"FAIL: Exceeds hard limit ({len(text)}/{LINKEDIN_CHAR_LIMIT} chars)"]
    if len(text) > LINKEDIN_CHAR_REC:
        issues.append(f"WARN: Over recommended length ({len(text)}/{LINKEDIN_CHAR_REC} chars)")
    lines = text.strip().split("\n")
    if not lines[0].strip():
        return False, ["FAIL: First line is empty — post needs a hook"]
    if len(post.get("hashtags", [])) == 0:
        return False, ["FAIL: No hashtags"]
    if "?" not in post["content"] and not any(
        w in post["content"].lower() for w in ["comment", "share", "tag", "let me know", "drop", "ask"]
    ):
        issues.append("WARN: No question or CTA — engagement may suffer")
    for pat in UNPROFESSIONAL_PATTERNS:
        if re.search(pat, text):
            issues.append(f"WARN: Unprofessional language pattern: {pat}")
    return True, issues

def quality_check_twitter(post: dict) -> tuple:
    issues = []
    for i, tweet in enumerate(post["thread"]):
        if len(tweet) > TWITTER_CHAR_LIMIT:
            return False, [f"FAIL: Tweet {i+1} exceeds 280 chars ({len(tweet)} chars)"]
    if len(post.get("hashtags", [])) > 3:
        issues.append("WARN: More than 3 hashtags — Twitter best practice is 1-2")
    return True, issues

def quality_check_instagram(post: dict) -> tuple:
    issues = []
    caption = post["caption"]
    if len(caption) > INSTAGRAM_CHAR_LIMIT:
        return False, [f"FAIL: Caption exceeds 2200-char limit ({len(caption)} chars)"]
    if len(post.get("hashtags", [])) > INSTAGRAM_HASHTAG_MAX:
        return False, [f"FAIL: Too many hashtags ({len(post['hashtags'])}/30)"]
    if not post.get("image_url"):
        issues.append("WARN: No image URL — required for live posting")
    return True, issues

def quality_check_facebook(post: dict) -> tuple:
    issues = []
    text = post["post_text"]
    if len(text) > 63206:
        return False, [f"FAIL: Exceeds Facebook hard limit ({len(text)}/63206 chars)"]
    if len(text) > 250:
        issues.append(f"WARN: Over recommended length for text-only ({len(text)}/250 chars) — add an image for best reach")
    if not post.get("content", "").strip():
        return False, ["FAIL: Post content is empty"]
    if "?" not in post.get("content", "") and not any(
        w in post.get("content", "").lower() for w in ["comment", "share", "tag", "tell me", "drop", "what's"]
    ):
        issues.append("WARN: No question or CTA — Facebook engagement drops without one")
    return True, issues

# ============================================================
# APPROVAL FILE CREATION
# ============================================================

def _expires_iso(hours: int = 24) -> str:
    return (datetime.utcnow() + timedelta(hours=hours)).strftime("%Y-%m-%dT%H:%M:%SZ")

def create_linkedin_approval_file(post: dict, dry_run: bool = False) -> str:
    PENDING_APPROVAL_DIR.mkdir(parents=True, exist_ok=True)
    filename = f"LINKEDIN_POST_{post['id']}_{today_str()}.md"
    file_path = PENDING_APPROVAL_DIR / filename
    expires = _expires_iso(24)
    content = f"""---
type: linkedin_post_approval
action: publish_linkedin_post
post_id: {post['id']}
content_type: {post['content_type']}
platform: linkedin
created: {post['created_at']}
expires: {expires}
status: pending
risk_level: medium
requested_by: social_media_auto_poster
simulation_mode: {str(SIMULATE_LINKEDIN).lower()}
---

# Approval Request: LinkedIn Post — {post['content_type'].replace('_', ' ').title()}

**Character count:** {post['char_count']} / 3000

## Post Preview

---

{post['post_text']}

---

## Details
- **Hashtags:** {', '.join(post['hashtags'])}
- **Mode:** {"SIMULATION — no real post" if SIMULATE_LINKEDIN else "LIVE — real LinkedIn API call"}
- **Expires:** {expires}

## To Approve → move to Approved/
## To Reject  → move to Rejected/

---
*Generated by social_media_auto_poster.py — AI Employee Vault Gold v2.0*
"""
    if not dry_run:
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)
    return str(file_path)

def create_twitter_approval_file(post: dict, dry_run: bool = False) -> str:
    PENDING_APPROVAL_DIR.mkdir(parents=True, exist_ok=True)
    is_thread = len(post["thread"]) > 1
    filename = f"TWITTER_POST_{post['id']}_{today_str()}.md"
    file_path = PENDING_APPROVAL_DIR / filename
    expires = _expires_iso(24)

    tweet_previews = "\n\n".join(
        f"**Tweet {i+1}/{len(post['thread'])}** ({len(t)} chars)\n\n> {t}"
        for i, t in enumerate(post["thread"])
    )

    content = f"""---
type: twitter_post_approval
action: publish_twitter_post
post_id: {post['id']}
content_type: {post['content_type']}
platform: twitter
is_thread: {is_thread}
tweet_count: {len(post['thread'])}
created: {post['created_at']}
expires: {expires}
status: pending
risk_level: medium
requested_by: social_media_auto_poster
simulation_mode: {str(SIMULATE_TWITTER).lower()}
---

# Approval Request: Twitter Post — {post['content_type'].replace('_', ' ').title()}

**Type:** {"Thread (" + str(len(post['thread'])) + " tweets)" if is_thread else "Single tweet"}

## Tweet Preview

---

{tweet_previews}

---

## Details
- **Hashtags:** {', '.join(post['hashtags'])}
- **Mode:** {"SIMULATION — no real tweet" if SIMULATE_TWITTER else "LIVE — real Twitter API v2 call"}
- **Expires:** {expires}

## To Approve → move to Approved/
## To Reject  → move to Rejected/

---
*Generated by social_media_auto_poster.py — AI Employee Vault Gold v2.0*
"""
    if not dry_run:
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)
    return str(file_path)

def create_instagram_approval_file(post: dict, dry_run: bool = False) -> str:
    PENDING_APPROVAL_DIR.mkdir(parents=True, exist_ok=True)
    filename = f"INSTAGRAM_POST_{post['id']}_{today_str()}.md"
    file_path = PENDING_APPROVAL_DIR / filename
    expires = _expires_iso(24)
    hashtag_str = " ".join(h if h.startswith("#") else f"#{h}" for h in post["hashtags"])

    content = f"""---
type: instagram_post_approval
action: publish_instagram_post
post_id: {post['id']}
content_type: {post['content_type']}
platform: instagram
post_type: {post.get('post_type', 'feed')}
created: {post['created_at']}
expires: {expires}
status: pending
risk_level: medium
requested_by: social_media_auto_poster
simulation_mode: {str(SIMULATE_INSTAGRAM).lower()}
---

# Approval Request: Instagram Post — {post['content_type'].replace('_', ' ').title()}

**Caption:** {post['char_count']} / 2200 chars
**Hashtags:** {len(post['hashtags'])} / 30

## IMAGE REQUIREMENT

> **IMAGE REQUIRED.** Instagram cannot post without an image or video.
> Image URL: {post.get('image_url') or 'NOT PROVIDED — add before going live'}
> Recommended: 1080x1350px (portrait) or 1080x1080px (square)

## Caption Preview

---

{post['caption']}

---

## Hashtags (post in first comment for cleaner look)

{hashtag_str}

---

## Details
- **Mode:** {"SIMULATION — no real post" if SIMULATE_INSTAGRAM else "LIVE — Instagram Graph API"}
- **Expires:** {expires}

## To Approve → move to Approved/
## To Reject  → move to Rejected/

---
*Generated by social_media_auto_poster.py — AI Employee Vault Gold v2.0*
"""
    if not dry_run:
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)
    return str(file_path)

def create_facebook_approval_file(post: dict, dry_run: bool = False) -> str:
    PENDING_APPROVAL_DIR.mkdir(parents=True, exist_ok=True)
    filename = f"FACEBOOK_POST_{post['id']}_{today_str()}.md"
    file_path = PENDING_APPROVAL_DIR / filename
    expires = _expires_iso(24)
    target_note = "personal profile" if post.get("target_type") == "profile" else "Facebook Page"

    content = f"""---
type: facebook_post_approval
action: publish_facebook_post
post_id: {post['id']}
content_type: {post['content_type']}
platform: facebook
target: {post.get('target_type', 'profile')}
created: {post['created_at']}
expires: {expires}
status: pending
risk_level: medium
requested_by: social_media_auto_poster
simulation_mode: {str(SIMULATE_FACEBOOK).lower()}
---

# Approval Request: Facebook Post — {post['content_type'].replace('_', ' ').title()}

**Target:** {target_note}
**Character count:** {post['char_count']} chars

## Post Preview

---

{post['post_text']}

---

## Details
- **Hashtags:** {', '.join(post['hashtags'])} (Facebook: 3 max — hashtags have minimal discovery impact)
- **Best posting time:** Wed–Sun 1–4 PM for organic reach
- **Mode:** {"SIMULATION — no real post" if SIMULATE_FACEBOOK else "LIVE — Facebook Graph API v21.0"}
- **Expires:** {expires}

## To Approve → move to Approved/
## To Reject  → move to Rejected/

---
*Generated by social_media_auto_poster.py — AI Employee Vault Gold v3.0*
"""
    if not dry_run:
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)
    return str(file_path)

def create_cross_post_approval_file(
    li_post: dict, tw_post: dict, ig_post: dict,
    dry_run: bool = False
) -> str:
    """Single approval file covering all 3 platforms."""
    PENDING_APPROVAL_DIR.mkdir(parents=True, exist_ok=True)
    post_id = generate_post_id()
    filename = f"CROSSPOST_{post_id}_{today_str()}.md"
    file_path = PENDING_APPROVAL_DIR / filename
    expires = _expires_iso(24)

    tw_preview = "\n\n".join(
        f"Tweet {i+1}: {t}" for i, t in enumerate(tw_post["thread"])
    )
    ig_tags = " ".join(h if h.startswith("#") else f"#{h}" for h in ig_post["hashtags"])

    content = f"""---
type: cross_post_approval
platforms: linkedin, twitter, instagram
post_id: {post_id}
created: {now_iso()}
expires: {expires}
status: pending
risk_level: medium
requested_by: social_media_auto_poster
---

# Cross-Platform Post Approval

**Approving this file publishes to all 3 platforms simultaneously.**

---

## LinkedIn Version ({li_post['char_count']} / 3000 chars)

{li_post['post_text']}

---

## Twitter Version ({"Thread: " + str(len(tw_post['thread'])) + " tweets" if len(tw_post['thread']) > 1 else "Single tweet"})

{tw_preview}

---

## Instagram Version ({ig_post['char_count']} / 2200 chars)

> IMAGE REQUIRED: {ig_post.get('image_url') or 'NOT PROVIDED — add before live posting'}

{ig_post['caption']}

Hashtags: {ig_tags}

---

## Platform Status

| Platform  | Mode        | Status |
|-----------|-------------|--------|
| LinkedIn  | {"SIMULATION" if SIMULATE_LINKEDIN  else "LIVE"} | Ready |
| Twitter   | {"SIMULATION" if SIMULATE_TWITTER   else "LIVE"} | Ready |
| Instagram | {"SIMULATION" if SIMULATE_INSTAGRAM else "LIVE"} | {"Ready" if ig_post.get('image_url') else "Needs image URL"} |

## To Approve → move to Approved/
## To Reject  → move to Rejected/

- **Expires:** {expires}

---
*Generated by social_media_auto_poster.py — AI Employee Vault Gold v2.0*
"""
    if not dry_run:
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)
    return str(file_path)

# ============================================================
# SCHEDULE HELPERS
# ============================================================

def get_next_posting_slots(count: int = 6) -> list:
    history = load_post_history()
    li_generated = history["platforms"].get("linkedin", {}).get("total_generated", 0)
    slots = []
    check_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    type_index = li_generated

    while len(slots) < count:
        check_date += timedelta(days=1)
        if check_date.weekday() in POSTING_DAYS:
            slots.append({
                "date":         check_date.strftime("%Y-%m-%d"),
                "weekday":      POSTING_DAYS[check_date.weekday()],
                "time":         f"{POSTING_HOUR:02d}:00",
                "datetime":     check_date.replace(hour=POSTING_HOUR),
                "content_type": CONTENT_TYPES[type_index % len(CONTENT_TYPES)],
            })
            type_index += 1
    return slots

def is_posting_day() -> bool:
    return datetime.now().weekday() in POSTING_DAYS

def is_posting_window() -> bool:
    now = datetime.now()
    target = now.replace(hour=POSTING_HOUR, minute=0, second=0)
    delta = abs((now - target).total_seconds()) / 60
    return delta <= POSTING_WINDOW_MINUTES

def already_posted_today(history: dict, platform: str = "linkedin") -> bool:
    today = today_str()
    return any(
        p.get("created_at", "").startswith(today)
        and p.get("status") in ("approved", "posted")
        and p.get("platform") == platform
        for p in history["posts"]
    )

def posts_this_week(history: dict, platform: str = "linkedin") -> int:
    week_ago = datetime.utcnow() - timedelta(days=7)
    return sum(
        1 for p in history["posts"]
        if p.get("platform") == platform
        and datetime.strptime(p["created_at"], "%Y-%m-%dT%H:%M:%SZ") > week_ago
        and p.get("status") in ("approved", "posted")
    )

# ============================================================
# CLI COMMANDS
# ============================================================

def run_generate(platform: str = "linkedin", dry_run: bool = False) -> None:
    print_section(f"Social Media Auto-Poster — Generate ({platform.title()})")
    stats   = load_vault_stats()
    history = load_post_history()
    content_type = select_content_type(history)

    print_info("Content type:", content_type.replace("_", " ").title())
    print_info("Vault stats:", f"{stats['done_total']} done, {stats['needs_action']} pending")
    print_info("Dry run:", dry_run)
    print()

    platforms_to_run = ["linkedin", "facebook", "twitter", "instagram"] if platform == "all" else [platform]

    for p in platforms_to_run:
        print(f"--- {p.upper()} ---")
        if p == "linkedin":
            post = generate_linkedin_content(content_type, history, stats)
            ok, issues = quality_check_linkedin(post)
        elif p == "facebook":
            post = generate_facebook_content(content_type, history, stats)
            ok, issues = quality_check_facebook(post)
        elif p == "twitter":
            post = generate_twitter_content(content_type, history, stats)
            ok, issues = quality_check_twitter(post)
        else:  # instagram
            post = generate_instagram_content(content_type, history, stats)
            ok, issues = quality_check_instagram(post)

        if issues:
            for issue in issues:
                print(f"  {issue}")

        if not ok:
            print(f"  Quality check FAILED — skipping {p}")
            log_action(f"Quality check failed for {p}", platform=p, status="failed")
            continue

        if p == "linkedin":
            preview = post["post_text"][:200]
        elif p == "facebook":
            preview = post["post_text"][:200]
        elif p == "twitter":
            preview = post["thread"][0][:200]
        else:
            preview = post["caption"][:200]

        print(f"  Preview: {preview}...")
        print(f"  Chars: {post.get('char_count', len(preview))}")

        if not dry_run:
            if p == "linkedin":
                ap = create_linkedin_approval_file(post)
                post["approval_file"] = ap
            elif p == "facebook":
                ap = create_facebook_approval_file(post)
                post["approval_file"] = ap
            elif p == "twitter":
                ap = create_twitter_approval_file(post)
                post["approval_file"] = ap
            else:
                ap = create_instagram_approval_file(post)
                post["approval_file"] = ap

            post["status"] = "pending_approval"
            history["posts"].append(post)
            history["platforms"].setdefault(p, {})
            history["platforms"][p]["total_generated"] = history["platforms"][p].get("total_generated", 0) + 1
            save_post_history(history)
            log_action(f"Generated {p} post {post['id']} — approval requested", platform=p)
            print(f"  Approval file: {Path(ap).name}")
        else:
            print("  [DRY RUN] No files written")
        print()


def run_schedule(platform: str = "linkedin", dry_run: bool = False) -> None:
    print_section(f"Social Media Auto-Poster — Schedule ({platform.title()})")
    slots = get_next_posting_slots(6)
    print_info("Platform:", platform)
    print_info("Upcoming M/W/F slots:", f"{len(slots)} found")
    print()
    for s in slots:
        print(f"  {s['date']} ({s['weekday']}) {s['time']} — {s['content_type'].replace('_', ' ').title()}")

    if not dry_run:
        plans_dir = VAULT_PATH / "Plans"
        plans_dir.mkdir(parents=True, exist_ok=True)
        rows = "\n".join(
            f"| {i+1} | {s['date']} ({s['weekday']}) | {s['time']} | {s['content_type'].replace('_', ' ').title()} | Pending |"
            for i, s in enumerate(slots)
        )
        plan_content = f"""---
type: social_media_schedule
platform: {platform}
created: {now_iso()}
status: active
posts_planned: {len(slots)}
---

# {platform.title()} Post Schedule — Created {today_str()}

| # | Date | Time | Content Type | Status |
|---|------|------|--------------|--------|
{rows}

Run on each posting day:
```bash
python social_media_auto_poster.py --generate --platform {platform}
```

Or let Ralph's loop handle it automatically via `--ralph-check`.

---
*Generated by social_media_auto_poster.py — AI Employee Vault Gold v2.0*
"""
        plan_file = plans_dir / f"{platform.upper()}_SCHEDULE_{today_str()}.md"
        with open(plan_file, "w", encoding="utf-8") as f:
            f.write(plan_content)
        print(f"\n  Plan saved: {plan_file.name}")
        log_action(f"Schedule plan created — {len(slots)} {platform} slots", platform=platform)
    else:
        print("\n  [DRY RUN] No plan file written")


def run_check_approved(dry_run: bool = False) -> None:
    print_section("Social Media Auto-Poster — Check Approved")

    def check_dir(directory: Path, label: str) -> None:
        if not directory.exists():
            return
        for f in directory.iterdir():
            if not f.is_file():
                continue
            for prefix in ("LINKEDIN_POST_", "FACEBOOK_POST_", "TWITTER_POST_", "INSTAGRAM_POST_", "CROSSPOST_"):
                if f.name.startswith(prefix):
                    platform = prefix.split("_")[0].lower()
                    print(f"  {label}: {f.name}")
                    if not dry_run:
                        done_path = DONE_DIR / f.name
                        DONE_DIR.mkdir(parents=True, exist_ok=True)
                        f.rename(done_path)
                        log_action(f"{label} processed: {f.name}", platform=platform)
                        print(f"    Moved to Done/")

    check_dir(APPROVED_DIR, "APPROVED")
    check_dir(REJECTED_DIR, "REJECTED")
    print("  Check complete")


def run_status() -> None:
    print_section("Social Media Auto-Poster — Status")
    history = load_vault_stats()
    post_history = load_post_history()

    print_info("Today:", today_str())
    print_info("Is posting day:", is_posting_day())
    print_info("In posting window:", is_posting_window())
    print()

    print("  === Vault Stats ===")
    print_info("  Done/:", history["done_total"])
    print_info("  Pending Approvals:", history["pending_approvals"])
    print_info("  Ralph Cycles:", history["ralph_cycles"])
    print()

    print("  === Post History ===")
    for p in ["linkedin", "facebook", "twitter", "instagram"]:
        ph = post_history["platforms"].get(p, {})
        print(f"  {p.title()}: {ph.get('total_generated', 0)} generated, {ph.get('total_approved', 0)} approved, {ph.get('total_posted', 0)} posted")
    print()

    print("  === Next Posting Slots (M/W/F 10:00) ===")
    for s in get_next_posting_slots(3):
        print(f"  {s['date']} ({s['weekday']}) — {s['content_type'].replace('_', ' ').title()}")

    sim_status = []
    if SIMULATE_LINKEDIN:  sim_status.append("LinkedIn: SIMULATION")
    if SIMULATE_FACEBOOK:  sim_status.append("Facebook: SIMULATION")
    if SIMULATE_TWITTER:   sim_status.append("Twitter: SIMULATION")
    if SIMULATE_INSTAGRAM: sim_status.append("Instagram: SIMULATION")
    print()
    print(f"  Mode: {' | '.join(sim_status) if sim_status else 'ALL LIVE'}")


def run_cross_post(content: str, dry_run: bool = False) -> None:
    print_section("Social Media Auto-Poster — Cross-Post")
    stats   = load_vault_stats()
    history = load_post_history()
    ct      = select_content_type(history)

    # Use provided content or generate fresh
    if not content:
        li_post = generate_linkedin_content(ct, history, stats)
        tw_post = generate_twitter_content(ct, history, stats)
        ig_post = generate_instagram_content(ct, history, stats)
    else:
        # User provided content — adapt per platform
        post_id = generate_post_id()
        li_post = {
            "id": post_id, "platform": "linkedin", "content_type": "custom",
            "content": content, "hashtags": ["#AI", "#Automation", "#Innovation"],
            "post_text": f"{content}\n\n#AI #Automation #Innovation",
            "char_count": len(content), "created_at": now_iso(), "status": "draft",
        }
        thread = split_for_twitter(content, ["#AI", "#BuildInPublic"])
        tw_post = {
            "id": post_id, "platform": "twitter", "content_type": "custom",
            "content": content, "hashtags": ["#AI", "#BuildInPublic"],
            "thread": thread, "is_thread": len(thread) > 1,
            "tweet_count": len(thread), "created_at": now_iso(), "status": "draft",
        }
        ig_caption = content[:2200]
        ig_post = {
            "id": post_id, "platform": "instagram", "content_type": "custom",
            "caption": ig_caption, "hashtags": ["#ai", "#automation", "#productivity",
            "#tech", "#innovation", "#startup", "#buildinpublic", "#developer",
            "#machinelearning", "#futureofwork"], "post_type": "feed",
            "image_url": "", "char_count": len(ig_caption), "created_at": now_iso(), "status": "draft",
        }

    print_info("LinkedIn:", f"{li_post['char_count']} chars")
    print_info("Twitter:", f"{'Thread: ' + str(len(tw_post['thread'])) + ' tweets' if len(tw_post['thread']) > 1 else 'Single tweet'}")
    print_info("Instagram:", f"{ig_post['char_count']} chars, {len(ig_post['hashtags'])} hashtags")
    print_info("Dry run:", dry_run)

    if not dry_run:
        ap = create_cross_post_approval_file(li_post, tw_post, ig_post)
        log_action("Cross-post approval created for LinkedIn + Twitter + Instagram", platform="all")
        print(f"\n  Approval file: {Path(ap).name}")
    else:
        print("\n  [DRY RUN] No files written")


def run_ralph_check(dry_run: bool = False) -> None:
    """
    Smart check designed for Ralph's OODA loop.
    1. Process any Approved/Rejected LINKEDIN_POST_* / TWITTER_POST_* / INSTAGRAM_POST_* files
    2. If today is M/W/F, within posting window, not yet posted, and under weekly cap: generate
    """
    history = load_post_history()

    # Step 1 — process approved/rejected
    run_check_approved(dry_run=dry_run)

    # Step 2 — generate if conditions met
    if not is_posting_day():
        print(f"  ralph-check: not a posting day ({datetime.now().strftime('%A')}), skipping generation")
        return

    if not is_posting_window():
        print(f"  ralph-check: outside posting window ({today_time_str()} vs {POSTING_HOUR:02d}:00 +/-{POSTING_WINDOW_MINUTES}m), skipping")
        return

    for p in ["linkedin", "facebook", "twitter", "instagram"]:
        if already_posted_today(history, p):
            print(f"  ralph-check: already posted {p} today, skipping")
            continue
        if posts_this_week(history, p) >= MAX_POSTS_PER_WEEK:
            print(f"  ralph-check: reached weekly cap ({MAX_POSTS_PER_WEEK}) for {p}, skipping")
            continue
        print(f"  ralph-check: generating {p} post...")
        run_generate(platform=p, dry_run=dry_run)

# ============================================================
# MAIN
# ============================================================

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Social Media Auto-Poster v3.0 — LinkedIn, Facebook, Twitter, Instagram"
    )
    parser.add_argument("--generate",      action="store_true", help="Generate a post draft and create approval request")
    parser.add_argument("--schedule",      action="store_true", help="Show and save next 6 posting slots")
    parser.add_argument("--check-approved", action="store_true", help="Process approved/rejected posts")
    parser.add_argument("--status",        action="store_true", help="Show system status and next posting slots")
    parser.add_argument("--ralph-check",   action="store_true", help="Smart check for Ralph's OODA loop")
    parser.add_argument("--cross-post",    action="store_true", help="Generate cross-platform post for all 3 platforms")
    parser.add_argument("--dry-run",       action="store_true", help="Preview actions without writing files")
    parser.add_argument("--platform",      default="linkedin",  help="Platform: linkedin | facebook | twitter | instagram | all")
    parser.add_argument("--content",       default="",          help="Content for --cross-post (optional)")

    args = parser.parse_args()

    if args.status:
        run_status()
    elif args.generate:
        run_generate(platform=args.platform, dry_run=args.dry_run)
    elif args.schedule:
        run_schedule(platform=args.platform, dry_run=args.dry_run)
    elif args.check_approved:
        run_check_approved(dry_run=args.dry_run)
    elif args.cross_post:
        run_cross_post(content=args.content, dry_run=args.dry_run)
    elif args.ralph_check:
        run_ralph_check(dry_run=args.dry_run)
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
