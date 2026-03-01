#!/usr/bin/env python3
"""
ralph_wiggum_loop.py — Gold Tier Autonomous Reasoning Loop
===========================================================
"I'm helping!" — Ralph Wiggum

Ralph is the AI Employee's autonomous brain. He runs continuously,
observes the vault state, reasons about what's most urgent, decides
on an action, executes it via Claude Code, and reflects on the result.

OODA Cycle: Observe → Orient → Decide → Act → Reflect

Usage:
    python ralph_wiggum_loop.py              # Normal continuous loop
    python ralph_wiggum_loop.py --dry-run    # Observe+Decide only, no Act
    python ralph_wiggum_loop.py --once       # Single cycle then exit
    python ralph_wiggum_loop.py --config PATH # Custom config file

Safety guarantees:
    - NEVER sends email without human approval
    - NEVER deletes files
    - ALWAYS logs every decision with reasoning
    - ALWAYS respects quiet hours
    - Pauses after 3 consecutive errors
"""

import argparse
import json
import logging
import os
import re
import signal
import subprocess
import sys
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional


# ─────────────────────────────────────────────────────────────────────────────
# CONFIGURATION
# ─────────────────────────────────────────────────────────────────────────────

VAULT_ROOT = Path(__file__).parent.resolve()
DEFAULT_CONFIG = VAULT_ROOT / "ralph_config.json"

RALPH_QUOTE = "I'm helping!"
VERSION = "1.0.0-gold"

# ─────────────────────────────────────────────────────────────────────────────
# CLAUDE EXECUTABLE DISCOVERY
# ─────────────────────────────────────────────────────────────────────────────

_claude_exe_cache: Optional[str] = None  # module-level cache


def find_claude_executable() -> str:
    """Locate the claude CLI executable and return its full path.

    Resolution order:
      1. Cached result from a previous call (fast path).
      2. 'claude' / 'claude.cmd' directly — works if PATH is set correctly.
      3. Common Windows npm global bin locations derived from APPDATA / LOCALAPPDATA.
      4. npm-reported prefix (shell subprocess to `npm config get prefix`).
      5. Raises RuntimeError with a helpful install message if nothing works.

    The resolved path is cached so PATH scanning only happens once per process.
    """
    global _claude_exe_cache
    if _claude_exe_cache:
        return _claude_exe_cache

    import shutil

    # ── Candidate list (ordered: most-likely first) ───────────────────────────
    candidates: list[str] = []

    # On Windows, npm CLI wrappers are installed as both a bare script and a
    # .cmd file. The .cmd form is required when launching without shell=True.
    is_windows = sys.platform.startswith("win")

    if is_windows:
        candidates.append("claude.cmd")   # npm .cmd wrapper (preferred on Windows)
        candidates.append("claude")       # may work if PATHEXT covers it

        # Derive paths from environment variables
        for env_var in ("APPDATA", "LOCALAPPDATA"):
            base = os.environ.get(env_var)
            if base:
                candidates.append(str(Path(base) / "npm" / "claude.cmd"))
                candidates.append(str(Path(base) / "npm" / "claude"))

        # npm global node_modules bin shim (less common but valid)
        for env_var in ("APPDATA", "LOCALAPPDATA"):
            base = os.environ.get(env_var)
            if base:
                candidates.append(str(
                    Path(base) / "npm" / "node_modules" / "@anthropic-ai"
                    / "claude-code" / "cli.js"
                ))
    else:
        # Unix / macOS: bare name + nvm / homebrew / system npm locations
        candidates.extend([
            "claude",
            str(Path.home() / ".npm-global" / "bin" / "claude"),
            "/usr/local/bin/claude",
            "/usr/bin/claude",
            str(Path.home() / ".local" / "bin" / "claude"),
        ])

    # ── Try shutil.which first (respects PATH) ───────────────────────────────
    for name in ("claude.cmd" if is_windows else "claude", "claude"):
        found = shutil.which(name)
        if found:
            _claude_exe_cache = found
            return _claude_exe_cache

    # ── Try every explicit candidate ─────────────────────────────────────────
    for candidate in candidates:
        p = Path(candidate)
        if p.is_file():
            _claude_exe_cache = str(p)
            return _claude_exe_cache

    # ── Last resort: ask npm where its prefix is ─────────────────────────────
    try:
        result = subprocess.run(
            ["npm", "config", "get", "prefix"],
            capture_output=True, text=True, timeout=10,
            shell=is_windows,
        )
        if result.returncode == 0:
            npm_prefix = result.stdout.strip()
            for name in ("claude.cmd", "claude"):
                p = Path(npm_prefix) / name
                if p.is_file():
                    _claude_exe_cache = str(p)
                    return _claude_exe_cache
    except Exception:
        pass

    # ── Nothing worked ───────────────────────────────────────────────────────
    raise RuntimeError(
        "Could not locate the 'claude' CLI executable.\n"
        "\n"
        "To fix this, install Claude Code CLI:\n"
        "  npm install -g @anthropic-ai/claude-code\n"
        "\n"
        "Then verify it is accessible:\n"
        "  where claude        (Windows)\n"
        "  which claude        (macOS / Linux)\n"
        "\n"
        "If claude is installed but Ralph still can't find it, set the full\n"
        "path in ralph_config.json under:\n"
        '  "claude_executable": "C:\\\\...\\\\claude.cmd"\n'
        "\n"
        f"Searched candidates:\n" + "\n".join(f"  - {c}" for c in candidates)
    )


def load_config(config_path: Path) -> dict:
    """Load ralph_config.json, falling back to safe defaults if missing."""
    defaults = {
        "loop": {
            "interval_minutes": 60,
            "max_actions_per_cycle": 3,
            "claude_timeout_seconds": 300,
            "startup_delay_seconds": 5,
        },
        "quiet_hours": {"enabled": True, "start_hour": 23, "end_hour": 6},
        "priorities": {
            "high_keyword_score": 100,
            "normal_score": 50,
            "low_score": 10,
            "age_bonus_per_hour": 2,
            "approval_expiry_urgent_hours": 4,
            "approval_expiry_score_boost": 200,
        },
        "safety": {
            "never_send_email_without_approval": True,
            "never_delete_files": True,
            "always_plan_multi_step": True,
            "max_consecutive_errors_before_pause": 3,
        },
        "logging": {
            "ralph_log_dir": "Logs/ralph",
            "state_file": "Logs/ralph/ralph_state.json",
            "keep_log_days": 30,
        },
        "actions": {
            "priority_queue": [
                "process_urgent_emails",
                "check_approval_expiry",
                "process_normal_emails",
                "generate_morning_briefing",
                "create_plan_for_complex_items",
                "generate_evening_summary",
                "update_dashboard",
                "health_check",
            ],
            "morning_briefing_hour": 8,
            "evening_summary_hour": 20,
            "briefing_window_minutes": 90,
        },
        "emergency_keywords": [
            "urgent", "asap", "critical", "important",
            "deadline", "emergency", "action required", "action needed",
            "failed", "error", "alert", "deleted", "security",
        ],
    }
    if config_path.exists():
        with open(config_path, "r", encoding="utf-8") as f:
            loaded = json.load(f)
        # Deep-merge loaded over defaults
        for section, values in loaded.items():
            if section.startswith("_"):
                continue
            if isinstance(values, dict) and section in defaults:
                defaults[section].update(values)
            else:
                defaults[section] = values
    return defaults


# ─────────────────────────────────────────────────────────────────────────────
# LOGGING SETUP
# ─────────────────────────────────────────────────────────────────────────────

def setup_logging(log_dir: Path) -> logging.Logger:
    """Configure dual logging: coloured console + daily file in Logs/ralph/."""
    log_dir.mkdir(parents=True, exist_ok=True)
    today = datetime.now().strftime("%Y-%m-%d")
    log_file = log_dir / f"{today}.log"

    logger = logging.getLogger("ralph")
    logger.setLevel(logging.DEBUG)
    logger.handlers.clear()

    # Console handler — INFO and above, with colour hints
    console = logging.StreamHandler(sys.stdout)
    console.setLevel(logging.INFO)
    console.setFormatter(logging.Formatter(
        "%(asctime)s [%(levelname)-8s] %(message)s",
        datefmt="%H:%M:%S",
    ))

    # File handler — DEBUG and above, with full timestamps
    file_h = logging.FileHandler(log_file, encoding="utf-8")
    file_h.setLevel(logging.DEBUG)
    file_h.setFormatter(logging.Formatter(
        "[%(asctime)s] [%(levelname)-8s] %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%SZ",
    ))

    logger.addHandler(console)
    logger.addHandler(file_h)
    return logger


# ─────────────────────────────────────────────────────────────────────────────
# STATE MANAGEMENT
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class RalphState:
    """Persisted state — survives restarts."""
    cycle_count: int = 0
    started_at: str = ""
    last_cycle_at: str = ""
    last_action: str = ""
    last_action_result: str = ""
    consecutive_errors: int = 0
    actions_today: list = field(default_factory=list)
    briefing_done_today: bool = False
    summary_done_today: bool = False
    total_items_processed: int = 0
    paused_until: str = ""    # ISO timestamp, empty = not paused

    @classmethod
    def load(cls, state_file: Path) -> "RalphState":
        if state_file.exists():
            try:
                with open(state_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                # Reset per-day fields if it's a new day
                last = data.get("last_cycle_at", "")
                if last:
                    last_date = last[:10]
                    today = datetime.now().strftime("%Y-%m-%d")
                    if last_date != today:
                        data["briefing_done_today"] = False
                        data["summary_done_today"] = False
                        data["actions_today"] = []
                return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})
            except Exception:
                pass  # Corrupted state — start fresh
        state = cls()
        state.started_at = datetime.utcnow().isoformat() + "Z"
        return state

    def save(self, state_file: Path) -> None:
        state_file.parent.mkdir(parents=True, exist_ok=True)
        with open(state_file, "w", encoding="utf-8") as f:
            json.dump(asdict(self), f, indent=2)


# ─────────────────────────────────────────────────────────────────────────────
# SYSTEM SNAPSHOT (Observe output)
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class ItemInfo:
    name: str
    priority: str          # high / normal / low
    item_type: str         # EMAIL / FILE / etc.
    age_hours: float
    has_emergency_keyword: bool


@dataclass
class ApprovalInfo:
    name: str
    expires_at: Optional[datetime]
    hours_until_expiry: float


@dataclass
class SystemSnapshot:
    """Complete picture of vault state at observation time."""
    observed_at: datetime
    needs_action_items: list              # List[ItemInfo]
    pending_approvals: list               # List[ApprovalInfo]
    active_plans: int
    time_context: str                     # morning/afternoon/evening/quiet
    is_quiet_hours: bool
    recent_errors: int
    dashboard_last_updated: str

    # Derived counts
    @property
    def high_count(self) -> int:
        return sum(1 for i in self.needs_action_items if i.priority == "high")

    @property
    def normal_count(self) -> int:
        return sum(1 for i in self.needs_action_items if i.priority == "normal")

    @property
    def low_count(self) -> int:
        return sum(1 for i in self.needs_action_items if i.priority == "low")

    @property
    def total_pending(self) -> int:
        return len(self.needs_action_items)

    @property
    def expiring_approvals(self) -> list:
        return [a for a in self.pending_approvals if a.hours_until_expiry < 4]


# ─────────────────────────────────────────────────────────────────────────────
# ACTION SCORING
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class ScoredAction:
    name: str
    score: float
    reason: str
    claude_prompt: str


# ─────────────────────────────────────────────────────────────────────────────
# PHASE 1 — OBSERVE
# ─────────────────────────────────────────────────────────────────────────────

class Observer:
    def __init__(self, vault: Path, cfg: dict, logger: logging.Logger):
        self.vault = vault
        self.cfg = cfg
        self.log = logger
        self.emergency_kw = [k.lower() for k in cfg.get("emergency_keywords", [])]

    def observe(self) -> SystemSnapshot:
        self.log.info("=" * 60)
        self.log.info("OBSERVE — scanning vault state...")

        now = datetime.now()
        items = self._scan_needs_action()
        approvals = self._scan_pending_approvals()
        plans = self._count_active_plans()
        errors = self._count_recent_errors()
        dashboard_ts = self._get_dashboard_timestamp()
        time_ctx = self._time_context(now)
        is_quiet = self._is_quiet_hours(now)

        snapshot = SystemSnapshot(
            observed_at=now,
            needs_action_items=items,
            pending_approvals=approvals,
            active_plans=plans,
            time_context=time_ctx,
            is_quiet_hours=is_quiet,
            recent_errors=errors,
            dashboard_last_updated=dashboard_ts,
        )

        self.log.info(
            f"  Needs_Action : {snapshot.total_pending} items  "
            f"(high={snapshot.high_count}, normal={snapshot.normal_count}, low={snapshot.low_count})"
        )
        self.log.info(f"  Approvals    : {len(approvals)} pending  ({len(snapshot.expiring_approvals)} expiring soon)")
        self.log.info(f"  Active plans : {plans}")
        self.log.info(f"  Time context : {time_ctx}  (quiet_hours={is_quiet})")
        self.log.info(f"  Recent errors: {errors}")

        return snapshot

    def _scan_needs_action(self) -> list:
        folder = self.vault / "Needs_Action"
        items = []
        if not folder.exists():
            return items

        now = datetime.now()
        for md_file in sorted(folder.glob("*.md")):
            try:
                content = md_file.read_text(encoding="utf-8", errors="replace")
                priority = self._extract_priority(content, md_file.name)
                item_type = self._extract_type(md_file.name)
                has_kw = self._has_emergency_keyword(md_file.name + " " + content[:500])
                if has_kw and priority == "normal":
                    priority = "high"

                # Age from filename date or file mtime
                age_hours = self._file_age_hours(md_file, now)

                items.append(ItemInfo(
                    name=md_file.name,
                    priority=priority,
                    item_type=item_type,
                    age_hours=age_hours,
                    has_emergency_keyword=has_kw,
                ))
            except Exception as e:
                self.log.debug(f"  Could not read {md_file.name}: {e}")
        return items

    def _extract_priority(self, content: str, filename: str) -> str:
        # Check frontmatter
        m = re.search(r"^priority:\s*(\w+)", content, re.MULTILINE | re.IGNORECASE)
        if m:
            p = m.group(1).lower()
            if p in ("high", "urgent", "critical"):
                return "high"
            if p in ("low",):
                return "low"
        # Check filename keywords
        lower = filename.lower()
        if any(k in lower for k in self.emergency_kw):
            return "high"
        return "normal"

    def _extract_type(self, filename: str) -> str:
        parts = filename.split("_")
        return parts[0].upper() if parts else "UNKNOWN"

    def _has_emergency_keyword(self, text: str) -> bool:
        lower = text.lower()
        return any(k in lower for k in self.emergency_kw)

    def _file_age_hours(self, path: Path, now: datetime) -> float:
        # Try to parse date from filename (YYYY-MM-DD pattern)
        m = re.search(r"(\d{4}-\d{2}-\d{2})", path.name)
        if m:
            try:
                file_date = datetime.strptime(m.group(1), "%Y-%m-%d")
                return (now - file_date).total_seconds() / 3600
            except ValueError:
                pass
        # Fall back to file mtime
        try:
            mtime = datetime.fromtimestamp(path.stat().st_mtime)
            return (now - mtime).total_seconds() / 3600
        except Exception:
            return 0.0

    def _scan_pending_approvals(self) -> list:
        folder = self.vault / "Pending_Approval"
        approvals = []
        if not folder.exists():
            return approvals

        now = datetime.now()
        for md_file in folder.glob("*.md"):
            try:
                content = md_file.read_text(encoding="utf-8", errors="replace")
                # Parse expires timestamp from frontmatter
                m = re.search(r"^expires:\s*(.+)$", content, re.MULTILINE)
                expires_at = None
                hours_left = 24.0  # default safe value
                if m:
                    try:
                        ts_str = m.group(1).strip().rstrip("Z")
                        expires_at = datetime.fromisoformat(ts_str)
                        hours_left = (expires_at - now).total_seconds() / 3600
                    except ValueError:
                        pass

                approvals.append(ApprovalInfo(
                    name=md_file.name,
                    expires_at=expires_at,
                    hours_until_expiry=hours_left,
                ))
            except Exception as e:
                self.log.debug(f"  Could not read approval {md_file.name}: {e}")
        return approvals

    def _count_active_plans(self) -> int:
        folder = self.vault / "Plans"
        if not folder.exists():
            return 0
        count = 0
        for md_file in folder.glob("*.md"):
            try:
                content = md_file.read_text(encoding="utf-8", errors="replace")
                m = re.search(r"^status:\s*(\w+)", content, re.MULTILINE | re.IGNORECASE)
                if m and m.group(1).lower() in ("active", "in_progress", "pending"):
                    count += 1
            except Exception:
                count += 1  # assume active if unreadable
        return count

    def _count_recent_errors(self) -> int:
        log_dir = self.vault / "Logs"
        today = datetime.now().strftime("%Y-%m-%d")
        log_file = log_dir / f"{today}.md"
        if not log_file.exists():
            return 0
        try:
            content = log_file.read_text(encoding="utf-8", errors="replace").lower()
            return content.count("status: failed") + content.count("status: error")
        except Exception:
            return 0

    def _get_dashboard_timestamp(self) -> str:
        db = self.vault / "Dashboard.md"
        if not db.exists():
            return ""
        try:
            content = db.read_text(encoding="utf-8", errors="replace")
            m = re.search(r"^\*\*Last Updated:\*\*\s*(.+)$", content, re.MULTILINE)
            return m.group(1).strip() if m else ""
        except Exception:
            return ""

    def _time_context(self, now: datetime) -> str:
        h = now.hour
        if self._is_quiet_hours(now):
            return "quiet"
        if 6 <= h < 12:
            return "morning"
        if 12 <= h < 18:
            return "afternoon"
        return "evening"

    def _is_quiet_hours(self, now: datetime) -> bool:
        if not self.cfg["quiet_hours"]["enabled"]:
            return False
        start = self.cfg["quiet_hours"]["start_hour"]
        end = self.cfg["quiet_hours"]["end_hour"]
        h = now.hour
        if start > end:  # spans midnight
            return h >= start or h < end
        return start <= h < end


# ─────────────────────────────────────────────────────────────────────────────
# PHASE 2 + 3 — ORIENT & DECIDE
# ─────────────────────────────────────────────────────────────────────────────

class Decider:
    """Orient (score) then Decide (select) the best action(s)."""

    def __init__(self, cfg: dict, state: RalphState, logger: logging.Logger):
        self.cfg = cfg
        self.state = state
        self.log = logger
        self.p = cfg["priorities"]
        self.act_cfg = cfg["actions"]

    def decide(self, snap: SystemSnapshot) -> list:
        """Return ordered list of ScoredAction to take this cycle (max N)."""
        self.log.info("ORIENT — analysing urgency and scoring actions...")

        if snap.is_quiet_hours:
            self.log.info("  Quiet hours active — monitoring only, no actions.")
            return []

        scores = self._score_all(snap)

        # Log top scores
        top = sorted(scores, key=lambda a: a.score, reverse=True)[:5]
        for a in top:
            self.log.info(f"  [{a.score:>6.0f}] {a.name:<35s} — {a.reason}")

        # Filter out zero-score actions
        actionable = [a for a in top if a.score > 0]

        # Cap at max_actions_per_cycle
        max_n = self.cfg["loop"]["max_actions_per_cycle"]
        chosen = actionable[:max_n]

        if chosen:
            self.log.info(f"DECIDE — selected {len(chosen)} action(s):")
            for i, a in enumerate(chosen, 1):
                self.log.info(f"  {i}. {a.name} (score={a.score:.0f})")
        else:
            self.log.info("DECIDE — no actionable items found. Ralph will rest.")

        return chosen

    def _score_all(self, snap: SystemSnapshot) -> list:
        scored = []
        for action_name in self.act_cfg["priority_queue"]:
            score, reason = self._score_action(action_name, snap)
            prompt = self._prompt_for(action_name, snap)
            if prompt:
                scored.append(ScoredAction(
                    name=action_name,
                    score=score,
                    reason=reason,
                    claude_prompt=prompt,
                ))
        return scored

    def _score_action(self, name: str, snap: SystemSnapshot):
        """Return (score, reason) for a given action."""
        p = self.p
        now = snap.observed_at

        if name == "process_urgent_emails":
            urgent = [i for i in snap.needs_action_items
                      if i.priority == "high" and i.item_type == "EMAIL"]
            if not urgent:
                return 0, "no urgent email items"
            score = len(urgent) * p["high_keyword_score"]
            # Age bonus from oldest item
            oldest = max(i.age_hours for i in urgent)
            score += oldest * p["age_bonus_per_hour"]
            return score, f"{len(urgent)} high-priority emails, oldest={oldest:.0f}h"

        if name == "check_approval_expiry":
            if not snap.expiring_approvals:
                return 0, "no approvals expiring soon"
            min_h = min(a.hours_until_expiry for a in snap.expiring_approvals)
            score = p["approval_expiry_score_boost"] + (4 - max(min_h, 0)) * 20
            return score, f"{len(snap.expiring_approvals)} approval(s) expiring in {min_h:.1f}h"

        if name == "process_normal_emails":
            items = [i for i in snap.needs_action_items if i.item_type == "EMAIL"]
            if not items:
                return 0, "no email items"
            score = len(items) * p["normal_score"]
            oldest = max(i.age_hours for i in items)
            score += oldest * p["age_bonus_per_hour"]
            return score, f"{len(items)} email items, oldest={oldest:.0f}h"

        if name == "generate_morning_briefing":
            if self.state.briefing_done_today:
                return 0, "briefing already done today"
            if snap.time_context != "morning":
                return 0, f"not morning (context={snap.time_context})"
            # Score higher the earlier in the morning window
            h = now.hour + now.minute / 60
            morning_h = self.act_cfg["morning_briefing_hour"]
            if abs(h - morning_h) <= 1.5:
                return 90, f"morning window, {abs(h - morning_h):.1f}h from target"
            return 0, "outside morning window"

        if name == "create_plan_for_complex_items":
            threshold = self.cfg.get("action_thresholds", {}).get("plan_required_if_items_above", 5)
            if snap.total_pending <= threshold or snap.active_plans > 0:
                return 0, f"only {snap.total_pending} items or plan already active"
            return 60, f"{snap.total_pending} items need organisation"

        if name == "generate_evening_summary":
            if self.state.summary_done_today:
                return 0, "summary already done today"
            if snap.time_context not in ("evening",):
                return 0, f"not evening (context={snap.time_context})"
            h = now.hour + now.minute / 60
            evening_h = self.act_cfg["evening_summary_hour"]
            if abs(h - evening_h) <= 1.5:
                return 85, f"evening window, {abs(h - evening_h):.1f}h from target"
            return 0, "outside evening window"

        if name == "update_dashboard":
            ts = snap.dashboard_last_updated
            if not ts:
                return 40, "dashboard timestamp unknown"
            try:
                # Parse "YYYY-MM-DD HH:MM:SS" format
                last = datetime.strptime(ts[:19], "%Y-%m-%d %H:%M:%S")
                hours_since = (now - last).total_seconds() / 3600
                if hours_since > 2:
                    return 35, f"dashboard last updated {hours_since:.1f}h ago"
                return 0, f"dashboard updated {hours_since:.1f}h ago (recent)"
            except Exception:
                return 30, "could not parse dashboard timestamp"

        if name == "health_check":
            if snap.recent_errors > 0:
                return 70, f"{snap.recent_errors} error(s) in today's log"
            return 0, "no recent errors"

        return 0, "unknown action"

    def _prompt_for(self, name: str, snap: SystemSnapshot) -> str:
        """Return the claude CLI prompt string for this action.

        NOTE on email actions:
          process_urgent_emails / process_normal_emails — these READ and TRIAGE
          EMAIL_*.md task files already sitting in Needs_Action/. They do NOT
          send any email. Processing = analyse → update Dashboard → move to Done
          → log. Use FILE_PROCESSOR_SKILL exactly as for FILE_*.md files.
          DO NOT invoke the email MCP send_email tool.
        """
        today = snap.observed_at.strftime("%Y-%m-%d")
        prompts = {
            # ── FILE PROCESSING (reads EMAIL_*.md task files, no sending) ────
            "process_urgent_emails": (
                "Read and process all HIGH priority EMAIL_*.md task files currently "
                "sitting in Needs_Action/ using FILE_PROCESSOR_SKILL. "
                "These are email notification task files — do NOT send any email. "
                "For each file: read the frontmatter and content, summarise the "
                "key information, move the file from Needs_Action/ to Done/, "
                "update Dashboard.md, and create a log entry. "
                "Focus on files with priority: high first."
            ),
            "process_normal_emails": (
                "Read and process all EMAIL_*.md task files currently sitting in "
                "Needs_Action/ using FILE_PROCESSOR_SKILL. "
                "These are email notification task files — do NOT send any email. "
                "For each file: read the frontmatter and content, summarise the "
                "key information, move the file from Needs_Action/ to Done/, "
                "update Dashboard.md, and create a log entry."
            ),
            # ── APPROVAL MONITORING ───────────────────────────────────────────
            "check_approval_expiry": (
                "Check the Pending_Approval/ folder for any APPROVAL_*.md files "
                "expiring within the next 4 hours. Read each file's 'expires' "
                "frontmatter field. Flag expiring approvals in Dashboard.md under "
                "Pending Approvals with a note showing hours remaining. "
                "Log the status of each approval file found."
            ),
            # ── BRIEFING — write markdown file to Plans/, do NOT send email ──
            "generate_morning_briefing": (
                f"Create a morning briefing markdown file at "
                f"Plans/BRIEFING_morning_{today}.md. "
                "Do NOT send any email. Write the briefing as a markdown file only. "
                "Include these sections: "
                "1) Today's date and time; "
                "2) Pending items count in Needs_Action/ (total, high, normal, low); "
                "3) List of any HIGH priority items needing attention; "
                "4) Any pending approvals and their expiry times; "
                "5) Active plans status; "
                "6) Suggested priorities for today. "
                "After creating the file, add a Dashboard.md Recent Activity entry: "
                f"'Morning briefing created: Plans/BRIEFING_morning_{today}.md'."
            ),
            # ── PLANNING ─────────────────────────────────────────────────────
            "create_plan_for_complex_items": (
                "Review the items in Needs_Action/ and identify any that require "
                "multi-step coordinated action (e.g. more than 5 related items, "
                "items referencing ongoing projects, or items needing sequential steps). "
                "For complex groups, create a plan file in Plans/ using "
                "PLAN_CREATOR_SKILL with clear steps, dependencies, and estimates. "
                "Update Dashboard.md with the new plan."
            ),
            # ── EVENING SUMMARY — write to Logs/, do NOT send email ──────────
            "generate_evening_summary": (
                "Create an end-of-day summary and update Dashboard.md. "
                "Do NOT send any email. "
                "Count: files processed today (check Done/ for today's date), "
                "items still pending in Needs_Action/, approvals resolved. "
                "Update Dashboard.md: increment Completed Tasks, set Pending Actions "
                "to current Needs_Action/ count, add Recent Activity entry. "
                "Append a summary section to today's log file in Logs/."
            ),
            # ── DASHBOARD ────────────────────────────────────────────────────
            "update_dashboard": (
                "Update Dashboard.md with current accurate system status. "
                "Count files in Needs_Action/ for Pending Actions. "
                "Count files in Done/ added today for Completed Tasks. "
                "Count files in Pending_Approval/ for Pending Approvals. "
                "Update Last Updated timestamp. Add a Recent Activity entry."
            ),
            # ── HEALTH CHECK ─────────────────────────────────────────────────
            "health_check": (
                "Check system health by reviewing the most recent log file in Logs/ "
                "for any entries with status: failed or status: error. "
                "Check that gmail_watcher.py and filesystem_watcher.py exist. "
                "Update the System Health section of Dashboard.md with findings. "
                "Log the health check result."
            ),
        }
        return prompts.get(name, "")


# ─────────────────────────────────────────────────────────────────────────────
# PHASE 4 — ACT
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class ActionResult:
    action_name: str
    success: bool
    exit_code: int
    duration_seconds: float
    output_preview: str   # First 500 chars of output
    error_preview: str


class Actor:
    """Execute chosen actions via Claude Code subprocess."""

    def __init__(self, vault: Path, cfg: dict, logger: logging.Logger, dry_run: bool = False):
        self.vault = vault
        self.cfg = cfg
        self.log = logger
        self.dry_run = dry_run
        self.timeout = cfg["loop"]["claude_timeout_seconds"]

        # Resolve claude executable once at Actor creation.
        # Prefer explicit override in config, then auto-discover.
        config_exe = cfg.get("claude_executable", "").strip()
        if config_exe and Path(config_exe).is_file():
            self._claude_exe: Optional[str] = config_exe
            self.log.info(f"  Claude executable (from config): {config_exe}")
        else:
            try:
                self._claude_exe = find_claude_executable()
                self.log.info(f"  Claude executable (auto-detected): {self._claude_exe}")
            except RuntimeError as e:
                self._claude_exe = None
                self.log.error(f"  {e}")

    def act(self, action: ScoredAction) -> ActionResult:
        self.log.info(f"ACT — executing: {action.name}")
        self.log.debug(f"  Prompt: {action.claude_prompt}")

        if self.dry_run:
            exe_display = self._claude_exe or "claude (not found)"
            self.log.info(f"  [DRY RUN] Would invoke: {exe_display!r} \"<prompt>\"")
            return ActionResult(
                action_name=action.name,
                success=True,
                exit_code=0,
                duration_seconds=0.0,
                output_preview="[dry-run — no action taken]",
                error_preview="",
            )

        # Guard: executable must be resolved before we can act
        if not self._claude_exe:
            msg = (
                "claude executable not found — cannot execute action. "
                "Run: npm install -g @anthropic-ai/claude-code"
            )
            self.log.error(f"  {msg}")
            return ActionResult(
                action_name=action.name,
                success=False,
                exit_code=-3,
                duration_seconds=0.0,
                output_preview="",
                error_preview=msg,
            )

        # Safety check: never send email without approval
        if self._is_email_send(action) and not self._has_approved_email():
            self.log.warning("  SAFETY GATE: email send action blocked — no file in Approved/")
            return ActionResult(
                action_name=action.name,
                success=False,
                exit_code=-1,
                duration_seconds=0.0,
                output_preview="",
                error_preview="Safety gate: email send requires approval file in Approved/",
            )

        start = time.monotonic()
        try:
            result = subprocess.run(
                [self._claude_exe, action.claude_prompt],
                cwd=str(self.vault),
                capture_output=True,
                text=True,
                timeout=self.timeout,
                encoding="utf-8",
                errors="replace",
            )
            duration = time.monotonic() - start
            success = result.returncode == 0
            out = (result.stdout or "").strip()
            err = (result.stderr or "").strip()

            status = "SUCCESS" if success else f"FAILED (exit={result.returncode})"
            self.log.info(f"  {status}  duration={duration:.0f}s")
            if out:
                self.log.debug(f"  stdout preview: {out[:300]}")
            if err:
                self.log.warning(f"  stderr: {err[:300]}")

            return ActionResult(
                action_name=action.name,
                success=success,
                exit_code=result.returncode,
                duration_seconds=duration,
                output_preview=out[:500],
                error_preview=err[:300],
            )

        except subprocess.TimeoutExpired:
            duration = time.monotonic() - start
            self.log.error(f"  TIMEOUT after {self.timeout}s")
            return ActionResult(
                action_name=action.name,
                success=False,
                exit_code=-2,
                duration_seconds=duration,
                output_preview="",
                error_preview=f"Claude timed out after {self.timeout}s",
            )
        except FileNotFoundError:
            msg = (
                f"Executable not found: {self._claude_exe!r}. "
                "The file may have been moved or uninstalled since Ralph started. "
                "Reinstall with: npm install -g @anthropic-ai/claude-code"
            )
            self.log.error(f"  {msg}")
            # Reset cache so next cycle re-discovers the path
            global _claude_exe_cache
            _claude_exe_cache = None
            self._claude_exe = None
            return ActionResult(
                action_name=action.name,
                success=False,
                exit_code=-3,
                duration_seconds=0.0,
                output_preview="",
                error_preview=msg,
            )
        except Exception as e:
            duration = time.monotonic() - start
            self.log.error(f"  Unexpected error: {e}")
            return ActionResult(
                action_name=action.name,
                success=False,
                exit_code=-4,
                duration_seconds=duration,
                output_preview="",
                error_preview=str(e),
            )

    # Actions that actually SEND email via the MCP send_email tool.
    # process_*_emails are FILE PROCESSING actions — they read EMAIL_*.md task
    # files and move them to Done/. They do NOT invoke the MCP server.
    _EMAIL_SEND_ACTIONS = frozenset({
        "send_email",
        "reply_to_email",
        "send_approval_notification",
    })

    def _is_email_send(self, action: ScoredAction) -> bool:
        """Return True only for actions that invoke the MCP send_email tool.

        Intentionally does NOT match process_urgent_emails or
        process_normal_emails — those read and triage EMAIL_*.md task files,
        they do not send any email.
        """
        return action.name in self._EMAIL_SEND_ACTIONS

    def _has_approved_email(self) -> bool:
        """Check if there's a file in Approved/ (human has approved an action)."""
        approved = self.vault / "Approved"
        if not approved.exists():
            return False
        return any(approved.glob("APPROVAL_*.md"))


# ─────────────────────────────────────────────────────────────────────────────
# PHASE 5 — REFLECT
# ─────────────────────────────────────────────────────────────────────────────

class Reflector:
    """Update state, log outcomes, ask 'Am I helping?'"""

    def __init__(self, cfg: dict, state: RalphState, logger: logging.Logger):
        self.cfg = cfg
        self.state = state
        self.log = logger

    def reflect(self, action: ScoredAction, result: ActionResult,
                before_snap: SystemSnapshot) -> None:
        self.log.info("REFLECT —")

        if result.success:
            self.state.consecutive_errors = 0
            self.state.last_action_result = "success"
            self.log.info(f"  Action '{action.name}' succeeded in {result.duration_seconds:.0f}s")

            # Track one-per-day actions
            if action.name == "generate_morning_briefing":
                self.state.briefing_done_today = True
            if action.name == "generate_evening_summary":
                self.state.summary_done_today = True

            # Ralph check
            self.log.info(f"  {RALPH_QUOTE}")
        else:
            self.state.consecutive_errors += 1
            self.state.last_action_result = "failed"
            self.log.warning(
                f"  Action '{action.name}' failed. "
                f"consecutive_errors={self.state.consecutive_errors}"
            )
            if result.error_preview:
                self.log.warning(f"  Error: {result.error_preview}")

            # Check pause threshold
            max_errors = self.cfg["safety"]["max_consecutive_errors_before_pause"]
            if self.state.consecutive_errors >= max_errors:
                pause_until = datetime.utcnow() + timedelta(hours=1)
                self.state.paused_until = pause_until.isoformat() + "Z"
                self.log.error(
                    f"  {max_errors} consecutive errors — Ralph is pausing until "
                    f"{self.state.paused_until}. Check logs and vault health."
                )

        # Update state fields
        self.state.last_action = action.name
        self.state.last_cycle_at = datetime.utcnow().isoformat() + "Z"
        if action.name not in self.state.actions_today:
            self.state.actions_today.append(action.name)


# ─────────────────────────────────────────────────────────────────────────────
# DAILY SUMMARY WRITER
# ─────────────────────────────────────────────────────────────────────────────

class DailySummaryWriter:
    """Append a daily autonomous-action summary to Logs/ralph/."""

    def __init__(self, log_dir: Path, logger: logging.Logger):
        self.log_dir = log_dir
        self.log = logger

    def append_cycle_summary(self, cycle: int, snap: SystemSnapshot,
                              actions_taken: list, results: list) -> None:
        today = datetime.now().strftime("%Y-%m-%d")
        summary_file = self.log_dir / f"{today}.log"
        now_str = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")

        lines = [
            f"\n{'─'*60}",
            f"CYCLE #{cycle} — {now_str}",
            f"  Observed : {snap.total_pending} pending, {snap.high_count} urgent, "
            f"{len(snap.pending_approvals)} approvals",
            f"  Context  : {snap.time_context}",
        ]
        if actions_taken:
            for action, result in zip(actions_taken, results):
                status = "✓" if result.success else "✗"
                lines.append(f"  [{status}] {action.name} ({result.duration_seconds:.0f}s)")
        else:
            lines.append("  [–] No actions taken (quiet hours or nothing to do)")
        lines.append(f"{'─'*60}")

        with open(summary_file, "a", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")


# ─────────────────────────────────────────────────────────────────────────────
# MAIN LOOP
# ─────────────────────────────────────────────────────────────────────────────

class RalphWiggumLoop:
    """Coordinates the full OODA cycle and manages the main loop."""

    def __init__(self, cfg: dict, vault: Path, dry_run: bool = False):
        self.cfg = cfg
        self.vault = vault
        self.dry_run = dry_run

        log_dir = vault / cfg["logging"]["ralph_log_dir"]
        self.log = setup_logging(log_dir)
        self.state_file = vault / cfg["logging"]["state_file"]
        self.state = RalphState.load(self.state_file)

        self.observer = Observer(vault, cfg, self.log)
        self.decider = Decider(cfg, self.state, self.log)
        self.actor = Actor(vault, cfg, self.log, dry_run=dry_run)
        self.reflector = Reflector(cfg, self.state, self.log)
        self.summariser = DailySummaryWriter(log_dir, self.log)

        self._running = True
        signal.signal(signal.SIGINT, self._handle_shutdown)
        signal.signal(signal.SIGTERM, self._handle_shutdown)

    def _handle_shutdown(self, signum, frame):
        self.log.info("")
        self.log.info("Shutdown signal received — finishing current cycle...")
        self._running = False

    def _is_paused(self) -> bool:
        """Check if Ralph is in error-pause mode."""
        if not self.state.paused_until:
            return False
        try:
            resume_at = datetime.fromisoformat(self.state.paused_until.rstrip("Z"))
            if datetime.utcnow() < resume_at:
                return True
            # Pause expired — reset
            self.log.info("Pause period over — Ralph is resuming.")
            self.state.paused_until = ""
            self.state.consecutive_errors = 0
            return False
        except Exception:
            self.state.paused_until = ""
            return False

    def run_cycle(self) -> None:
        """Execute one full OODA cycle."""
        self.state.cycle_count += 1
        cycle_num = self.state.cycle_count

        # ── HEARTBEAT ────────────────────────────────────────────────────────
        self.log.info("")
        self.log.info("╔" + "═" * 58 + "╗")
        self.log.info(f"║  Ralph Wiggum — Cycle #{cycle_num:<4d}  v{VERSION:<10s}  {RALPH_QUOTE:<14s}  ║")
        self.log.info(f"║  {datetime.now().strftime('%Y-%m-%d %H:%M:%S'):<56s}  ║")
        self.log.info("╚" + "═" * 58 + "╝")

        if self._is_paused():
            self.log.warning(f"Ralph is paused until {self.state.paused_until}. Skipping cycle.")
            self.state.save(self.state_file)
            return

        # ── OBSERVE ──────────────────────────────────────────────────────────
        snap = self.observer.observe()

        # ── ORIENT + DECIDE ──────────────────────────────────────────────────
        actions = self.decider.decide(snap)

        # ── ACT + REFLECT ────────────────────────────────────────────────────
        results = []
        for i, action in enumerate(actions, 1):
            self.log.info(f"── Action {i}/{len(actions)}: {action.name} ──")
            result = self.actor.act(action)
            self.reflector.reflect(action, result, snap)
            results.append(result)
            self.state.save(self.state_file)

            # Stop executing further actions if we hit errors
            if not result.success and self._is_paused():
                self.log.warning("Paused mid-cycle due to repeated errors.")
                break

        # ── DAILY SUMMARY ────────────────────────────────────────────────────
        self.summariser.append_cycle_summary(cycle_num, snap, actions, results)

        # ── FINAL STATE SAVE ─────────────────────────────────────────────────
        self.state.last_cycle_at = datetime.utcnow().isoformat() + "Z"
        self.state.save(self.state_file)

        self.log.info(
            f"Cycle #{cycle_num} complete. "
            f"Actions taken: {len(actions)}. "
            f"Total items ever processed: {self.state.total_items_processed}."
        )

    def run(self, once: bool = False) -> None:
        """Main entry point — run continuously or for a single cycle."""
        interval = self.cfg["loop"]["interval_minutes"] * 60
        delay = self.cfg["loop"]["startup_delay_seconds"]

        self.log.info("")
        self.log.info("╔══════════════════════════════════════════════════════════╗")
        self.log.info("║         RALPH WIGGUM AUTONOMOUS LOOP — STARTING          ║")
        self.log.info(f"║  Gold Tier v{VERSION:<10s}  Vault: {str(self.vault)[:25]:<25s}  ║")
        self.log.info(f"║  Interval: {self.cfg['loop']['interval_minutes']}min   "
                      f"Max actions/cycle: {self.cfg['loop']['max_actions_per_cycle']}   "
                      f"Dry-run: {str(self.dry_run):<5s}        ║")
        self.log.info(f"║  Quiet hours: "
                      f"{self.cfg['quiet_hours']['start_hour']:02d}:00–"
                      f"{self.cfg['quiet_hours']['end_hour']:02d}:00   "
                      f"Resumed from cycle #{self.state.cycle_count:<6d}          ║")
        self.log.info("╚══════════════════════════════════════════════════════════╝")
        self.log.info(f"Startup delay: {delay}s — then first cycle begins.")
        self.log.info("Press Ctrl+C to stop gracefully.")

        if delay > 0 and not once:
            time.sleep(delay)

        try:
            while self._running:
                self.run_cycle()

                if once or not self._running:
                    break

                self.log.info(f"Next cycle in {self.cfg['loop']['interval_minutes']} minutes. Sleeping...")
                # Sleep in 10-second chunks so Ctrl+C is responsive
                for _ in range(int(interval / 10)):
                    if not self._running:
                        break
                    time.sleep(10)

        finally:
            self.log.info("")
            self.log.info("══════════════════════════════════════════════════════════")
            self.log.info(f"Ralph Wiggum shutting down cleanly after {self.state.cycle_count} cycles.")
            self.log.info(f"Actions taken today: {self.state.actions_today}")
            self.log.info("State saved. See you next time! I was helping!")
            self.log.info("══════════════════════════════════════════════════════════")
            self.state.save(self.state_file)


# ─────────────────────────────────────────────────────────────────────────────
# ENTRY POINT
# ─────────────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Ralph Wiggum — Gold Tier Autonomous Reasoning Loop",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python ralph_wiggum_loop.py                 # Normal continuous loop
  python ralph_wiggum_loop.py --dry-run       # Observe+Decide only, no Act
  python ralph_wiggum_loop.py --once          # One cycle then exit
  python ralph_wiggum_loop.py --config PATH   # Custom config file
        """,
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=DEFAULT_CONFIG,
        help=f"Path to ralph_config.json (default: {DEFAULT_CONFIG})",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Observe and decide but do not invoke Claude Code",
    )
    parser.add_argument(
        "--once",
        action="store_true",
        help="Run one cycle then exit (useful for testing)",
    )
    parser.add_argument(
        "--vault",
        type=Path,
        default=VAULT_ROOT,
        help=f"Path to vault root (default: {VAULT_ROOT})",
    )

    args = parser.parse_args()
    cfg = load_config(args.config)

    ralph = RalphWiggumLoop(cfg=cfg, vault=args.vault, dry_run=args.dry_run)
    ralph.run(once=args.once)


if __name__ == "__main__":
    main()
