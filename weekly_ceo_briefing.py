#!/usr/bin/env python3
"""
weekly_ceo_briefing.py — Gold Tier Weekly CEO Briefing Generator
=================================================================
Generates a comprehensive business audit report every Sunday covering the
past 7 days of AI Employee activity.

Sections produced:
  1. Executive Summary   — tasks, emails, approvals, plans at a glance
  2. Key Metrics         — processing stats, success rate, throughput
  3. Email Analysis      — top senders, domains, priority breakdown
  4. Ralph Autonomous    — OODA cycles, actions taken, errors
  5. Upcoming Week       — pending backlog, expiring approvals, recommendations

Output: Reports/CEO_Briefing_YYYY-MM-DD.md

Usage:
    python weekly_ceo_briefing.py                   # Generate for last 7 days
    python weekly_ceo_briefing.py --date 2026-02-23 # Specific week-end date
    python weekly_ceo_briefing.py --days 14         # Custom lookback window
    python weekly_ceo_briefing.py --stdout          # Print to console instead of file
"""

import argparse
import json
import re
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Optional


# ─────────────────────────────────────────────────────────────────────────────
# CONSTANTS & PATHS
# ─────────────────────────────────────────────────────────────────────────────

VAULT_ROOT = Path(__file__).parent.resolve()
REPORTS_DIR = VAULT_ROOT / "Reports"
LOGS_DIR = VAULT_ROOT / "Logs"
RALPH_LOGS_DIR = VAULT_ROOT / "Logs" / "ralph"

VERSION = "1.0.0-gold"

# Folders that represent completed work
DONE_DIR = VAULT_ROOT / "Done"
NEEDS_ACTION_DIR = VAULT_ROOT / "Needs_Action"
PENDING_APPROVAL_DIR = VAULT_ROOT / "Pending_Approval"
APPROVED_DIR = VAULT_ROOT / "Approved"
REJECTED_DIR = VAULT_ROOT / "Rejected"
PLANS_DIR = VAULT_ROOT / "Plans"


# ─────────────────────────────────────────────────────────────────────────────
# DATA STRUCTURES
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class LogEntry:
    """One parsed entry from a daily Logs/YYYY-MM-DD.md file."""
    timestamp: str
    action_type: str
    actor: str
    status: str         # success | failed | pending
    title: str          # from "## Action: ..." heading
    notes: str          # free-text body after the heading


@dataclass
class DailyLogSummary:
    """Parsed summary block from the top of a daily log file."""
    date: date
    total_actions: int = 0
    successful: int = 0
    failed: int = 0
    pending: int = 0
    entries: list = field(default_factory=list)   # List[LogEntry]


@dataclass
class EmailTaskInfo:
    """Metadata extracted from an EMAIL_*.md task file."""
    filename: str
    sender: str           # raw "From" field
    sender_domain: str    # e.g. "github.com"
    subject: str
    received: str         # ISO timestamp string
    priority: str         # high / normal / low
    status: str           # pending / done / processed
    folder: str           # Needs_Action / Done


@dataclass
class ApprovalRecord:
    """Metadata from an APPROVAL_*.md file."""
    filename: str
    action: str
    created: str
    expires: str
    risk_level: str
    folder: str           # Done / Pending_Approval / Approved / Rejected
    outcome: str          # approved / rejected / pending / expired


@dataclass
class RalphCycle:
    """One parsed OODA cycle from a Logs/ralph/YYYY-MM-DD.log file."""
    cycle_num: int
    timestamp: str
    pending_count: int
    urgent_count: int
    approval_count: int
    context: str
    actions: list         # List of (action_name, success, duration_s)


@dataclass
class WeeklyMetrics:
    """Aggregated metrics across the full reporting window."""
    # Date range
    week_start: date = field(default_factory=date.today)
    week_end: date = field(default_factory=date.today)

    # Task processing
    total_actions: int = 0
    successful_actions: int = 0
    failed_actions: int = 0
    files_processed: int = 0
    files_created: int = 0

    # Email pipeline
    emails_received: int = 0       # EMAIL_*.md files created this week
    emails_processed: int = 0      # EMAIL_*.md files in Done/
    emails_pending: int = 0        # EMAIL_*.md in Needs_Action/
    email_senders: Counter = field(default_factory=Counter)
    email_domains: Counter = field(default_factory=Counter)
    email_priorities: Counter = field(default_factory=Counter)

    # Approvals
    approvals_requested: int = 0
    approvals_granted: int = 0
    approvals_rejected: int = 0
    approvals_pending: int = 0
    approvals_expired: int = 0

    # Ralph autonomous loop
    ralph_cycles: int = 0
    ralph_actions_taken: int = 0
    ralph_actions_succeeded: int = 0
    ralph_actions_failed: int = 0
    ralph_action_types: Counter = field(default_factory=Counter)

    # Plans
    plans_active: int = 0
    plans_created_this_week: int = 0

    # Action type breakdown
    action_types: Counter = field(default_factory=Counter)

    @property
    def success_rate(self) -> float:
        if self.total_actions == 0:
            return 0.0
        return self.successful_actions / self.total_actions * 100

    @property
    def email_process_rate(self) -> float:
        total = self.emails_processed + self.emails_pending
        if total == 0:
            return 0.0
        return self.emails_processed / total * 100

    @property
    def approval_accept_rate(self) -> float:
        decided = self.approvals_granted + self.approvals_rejected
        if decided == 0:
            return 0.0
        return self.approvals_granted / decided * 100

    @property
    def ralph_success_rate(self) -> float:
        if self.ralph_actions_taken == 0:
            return 0.0
        return self.ralph_actions_succeeded / self.ralph_actions_taken * 100


# ─────────────────────────────────────────────────────────────────────────────
# PARSERS
# ─────────────────────────────────────────────────────────────────────────────

class DailyLogParser:
    """Parses vault daily log files: Logs/YYYY-MM-DD.md"""

    # Regex patterns for the structured frontmatter blocks inside logs
    _ENTRY_PATTERN = re.compile(
        r"---\s*\n"
        r"timestamp:\s*(?P<timestamp>[^\n]+)\n"
        r"action_type:\s*(?P<action_type>[^\n]+)\n"
        r"actor:\s*(?P<actor>[^\n]+)\n"
        r"status:\s*(?P<status>[^\n]+)\n"
        r"---\s*\n"
        r"(?:## Action:\s*(?P<title>[^\n]+)\n)?",
        re.MULTILINE,
    )
    _SUMMARY_TOTAL = re.compile(r"- Total actions:\s*(\d+)")
    _SUMMARY_SUCCESS = re.compile(r"- Successful:\s*(\d+)")
    _SUMMARY_FAILED = re.compile(r"- Failed:\s*(\d+)")
    _SUMMARY_PENDING = re.compile(r"- Pending:\s*(\d+)")

    def parse_file(self, log_file: Path) -> Optional[DailyLogSummary]:
        """Parse a single daily log file and return a DailyLogSummary."""
        if not log_file.exists():
            return None

        try:
            content = log_file.read_text(encoding="utf-8", errors="replace")
        except OSError:
            return None

        # Extract date from filename
        try:
            log_date = date.fromisoformat(log_file.stem)
        except ValueError:
            return None

        summary = DailyLogSummary(date=log_date)

        # Parse summary block at top of file
        if m := self._SUMMARY_TOTAL.search(content):
            summary.total_actions = int(m.group(1))
        if m := self._SUMMARY_SUCCESS.search(content):
            summary.successful = int(m.group(1))
        if m := self._SUMMARY_FAILED.search(content):
            summary.failed = int(m.group(1))
        if m := self._SUMMARY_PENDING.search(content):
            summary.pending = int(m.group(1))

        # Parse individual log entries
        for match in self._ENTRY_PATTERN.finditer(content):
            entry = LogEntry(
                timestamp=match.group("timestamp").strip(),
                action_type=match.group("action_type").strip(),
                actor=match.group("actor").strip(),
                status=match.group("status").strip(),
                title=(match.group("title") or "").strip(),
                notes="",  # body text is not needed for metrics
            )
            summary.entries.append(entry)

        return summary

    def parse_week(self, week_end: date, days: int = 7) -> list:
        """Parse all daily logs for the given lookback window.
        Returns List[DailyLogSummary], skipping missing days silently."""
        summaries = []
        for offset in range(days - 1, -1, -1):
            target = week_end - timedelta(days=offset)
            log_file = LOGS_DIR / f"{target.isoformat()}.md"
            summary = self.parse_file(log_file)
            if summary:
                summaries.append(summary)
        return summaries


class EmailTaskParser:
    """Parses EMAIL_*.md task files from Needs_Action/ and Done/."""

    _FRONTMATTER_PATTERN = re.compile(r"^---\s*\n(.*?)\n---", re.DOTALL)
    _FIELD_PATTERN = re.compile(r'^(\w+):\s*"?([^"\n]*)"?\s*$', re.MULTILINE)

    def parse_file(self, md_file: Path, folder: str) -> Optional[EmailTaskInfo]:
        """Extract metadata from a single EMAIL_*.md file."""
        if not md_file.name.startswith("EMAIL_"):
            return None
        try:
            content = md_file.read_text(encoding="utf-8", errors="replace")
        except OSError:
            return None

        # Parse YAML-ish frontmatter
        fields: dict[str, str] = {}
        if fm := self._FRONTMATTER_PATTERN.match(content):
            for key, val in self._FIELD_PATTERN.findall(fm.group(1)):
                fields[key.lower()] = val.strip().strip('"')

        sender = fields.get("from", "Unknown")
        domain = self._extract_domain(sender)

        return EmailTaskInfo(
            filename=md_file.name,
            sender=sender,
            sender_domain=domain,
            subject=fields.get("subject", md_file.stem),
            received=fields.get("received", ""),
            priority=fields.get("priority", "normal").lower(),
            status=fields.get("status", "pending").lower(),
            folder=folder,
        )

    def _extract_domain(self, sender: str) -> str:
        """Extract domain from 'Name <user@domain.com>' or 'user@domain.com'."""
        email_match = re.search(r"@([\w.\-]+)", sender)
        if email_match:
            return email_match.group(1).lower()
        return "unknown"

    def scan_folder(self, folder: Path, folder_name: str) -> list:
        """Return List[EmailTaskInfo] for all EMAIL_*.md in a folder."""
        if not folder.exists():
            return []
        results = []
        for md_file in folder.glob("EMAIL_*.md"):
            info = self.parse_file(md_file, folder_name)
            if info:
                results.append(info)
        return results

    def is_from_this_week(self, info: EmailTaskInfo, week_start: date) -> bool:
        """Check if the email was received during the reporting window."""
        if not info.received:
            return True  # can't tell — include conservatively
        try:
            received_date = datetime.fromisoformat(
                info.received.rstrip("Z")
            ).date()
            return received_date >= week_start
        except ValueError:
            return True


class ApprovalParser:
    """Parses APPROVAL_*.md files from Done/, Pending_Approval/, etc."""

    _FRONTMATTER_PATTERN = re.compile(r"^---\s*\n(.*?)\n---", re.DOTALL)
    _FIELD_PATTERN = re.compile(r'^(\w+):\s*"?([^"\n]*)"?\s*$', re.MULTILINE)

    # Map folder name → default outcome
    _FOLDER_OUTCOMES = {
        "Done": "resolved",        # resolved = approved or rejected (check filename/status)
        "Pending_Approval": "pending",
        "Approved": "approved",
        "Rejected": "rejected",
    }

    def parse_file(self, md_file: Path, folder: str) -> Optional[ApprovalRecord]:
        if not md_file.name.startswith("APPROVAL_"):
            return None
        try:
            content = md_file.read_text(encoding="utf-8", errors="replace")
        except OSError:
            return None

        fields: dict[str, str] = {}
        if fm := self._FRONTMATTER_PATTERN.match(content):
            for key, val in self._FIELD_PATTERN.findall(fm.group(1)):
                fields[key.lower()] = val.strip().strip('"')

        # Determine outcome from folder + status field
        status_field = fields.get("status", "").lower()
        outcome = self._FOLDER_OUTCOMES.get(folder, "unknown")
        if folder == "Done":
            # In Done/, status field tells us the real outcome
            if "approved" in content.lower() and "APPROVED" in content:
                outcome = "approved"
            elif "rejected" in content.lower():
                outcome = "rejected"
            elif status_field == "expired":
                outcome = "expired"
            else:
                outcome = "approved"  # default for Done/ approvals

        return ApprovalRecord(
            filename=md_file.name,
            action=fields.get("action", "unknown action"),
            created=fields.get("created", ""),
            expires=fields.get("expires", ""),
            risk_level=fields.get("risk_level", "unknown"),
            folder=folder,
            outcome=outcome,
        )

    def scan_folder(self, folder: Path, folder_name: str) -> list:
        if not folder.exists():
            return []
        results = []
        for md_file in folder.glob("APPROVAL_*.md"):
            rec = self.parse_file(md_file, folder_name)
            if rec:
                results.append(rec)
        return results


class RalphLogParser:
    """Parses Logs/ralph/YYYY-MM-DD.log cycle summary files."""

    # Each cycle block starts with a line of ─ characters
    _DIVIDER = re.compile(r"^─{30,}", re.MULTILINE)
    _CYCLE_HEADER = re.compile(
        r"CYCLE #(\d+)\s*[—–-]+\s*(\S+)"      # CYCLE #N — timestamp
    )
    _OBSERVED = re.compile(
        r"Observed\s*:\s*(\d+)\s*pending.*?(\d+)\s*urgent.*?(\d+)\s*approval",
        re.IGNORECASE,
    )
    _CONTEXT = re.compile(r"Context\s*:\s*(\w+)", re.IGNORECASE)
    _ACTION_LINE = re.compile(
        r"\[(✓|✗|–|-)\]\s*([\w_]+).*?(?:\((\d+)s\))?$"
    )

    def parse_file(self, log_file: Path) -> list:
        """Return List[RalphCycle] parsed from one Ralph daily log."""
        if not log_file.exists():
            return []
        try:
            content = log_file.read_text(encoding="utf-8", errors="replace")
        except OSError:
            return []

        cycles = []
        # Split on divider lines to get individual cycle blocks
        blocks = self._DIVIDER.split(content)

        for block in blocks:
            block = block.strip()
            if not block:
                continue

            # Must have a CYCLE # header
            header_match = self._CYCLE_HEADER.search(block)
            if not header_match:
                continue

            cycle_num = int(header_match.group(1))
            timestamp = header_match.group(2)

            # Observation counts
            pending = urgent = approvals = 0
            if obs := self._OBSERVED.search(block):
                pending = int(obs.group(1))
                urgent = int(obs.group(2))
                approvals = int(obs.group(3))

            # Time context
            context = "unknown"
            if ctx := self._CONTEXT.search(block):
                context = ctx.group(1)

            # Actions taken (✓ = success, ✗ = failure, – = skipped)
            actions = []
            for line in block.splitlines():
                if action_m := self._ACTION_LINE.search(line.strip()):
                    symbol = action_m.group(1)
                    action_name = action_m.group(2)
                    duration = int(action_m.group(3)) if action_m.group(3) else 0
                    success = symbol == "✓"
                    actions.append((action_name, success, duration))

            cycles.append(RalphCycle(
                cycle_num=cycle_num,
                timestamp=timestamp,
                pending_count=pending,
                urgent_count=urgent,
                approval_count=approvals,
                context=context,
                actions=actions,
            ))

        return cycles

    def parse_week(self, week_end: date, days: int = 7) -> list:
        """Parse all Ralph logs in the window. Returns List[RalphCycle]."""
        all_cycles = []
        for offset in range(days - 1, -1, -1):
            target = week_end - timedelta(days=offset)
            log_file = RALPH_LOGS_DIR / f"{target.isoformat()}.log"
            all_cycles.extend(self.parse_file(log_file))
        return all_cycles


# ─────────────────────────────────────────────────────────────────────────────
# METRICS AGGREGATOR
# ─────────────────────────────────────────────────────────────────────────────

class MetricsAggregator:
    """Combines all parsed data into a single WeeklyMetrics object."""

    def aggregate(
        self,
        week_end: date,
        days: int,
        daily_summaries: list,
        email_tasks: list,
        approvals: list,
        ralph_cycles: list,
    ) -> WeeklyMetrics:

        week_start = week_end - timedelta(days=days - 1)
        m = WeeklyMetrics(week_start=week_start, week_end=week_end)

        # ── Daily log metrics ─────────────────────────────────────────────────
        for summary in daily_summaries:
            m.total_actions += summary.total_actions
            m.successful_actions += summary.successful
            m.failed_actions += summary.failed

            for entry in summary.entries:
                m.action_types[entry.action_type] += 1
                if "file_created" in entry.action_type:
                    m.files_created += 1
                if "file_processed" in entry.action_type or "file_moved" in entry.action_type:
                    m.files_processed += 1
                if "approval_requested" in entry.action_type:
                    m.approvals_requested += 1

        # ── Email task metrics ────────────────────────────────────────────────
        email_parser = EmailTaskParser()
        for info in email_tasks:
            if info.folder == "Needs_Action":
                m.emails_pending += 1
            else:
                m.emails_processed += 1

            # Only count as "received this week" if within window
            if email_parser.is_from_this_week(info, week_start):
                m.emails_received += 1

            # Sender analytics (top sender name before angle bracket)
            display_name = re.sub(r"\s*<[^>]+>", "", info.sender).strip()
            if not display_name:
                display_name = info.sender_domain
            m.email_senders[display_name or "Unknown"] += 1
            m.email_domains[info.sender_domain] += 1
            m.email_priorities[info.priority] += 1

        # ── Approval metrics ──────────────────────────────────────────────────
        for rec in approvals:
            if rec.outcome == "approved":
                m.approvals_granted += 1
            elif rec.outcome == "rejected":
                m.approvals_rejected += 1
            elif rec.outcome == "pending":
                m.approvals_pending += 1
            elif rec.outcome == "expired":
                m.approvals_expired += 1

        # ── Ralph metrics ─────────────────────────────────────────────────────
        m.ralph_cycles = len(ralph_cycles)
        for cycle in ralph_cycles:
            for action_name, success, _duration in cycle.actions:
                if action_name in ("–", "-") or not action_name:
                    continue
                m.ralph_actions_taken += 1
                m.ralph_action_types[action_name] += 1
                if success:
                    m.ralph_actions_succeeded += 1
                else:
                    m.ralph_actions_failed += 1

        # ── Plans ─────────────────────────────────────────────────────────────
        m.plans_active = self._count_active_plans()
        m.plans_created_this_week = self._count_plans_created_this_week(week_start)

        return m

    def _count_active_plans(self) -> int:
        if not PLANS_DIR.exists():
            return 0
        count = 0
        for f in PLANS_DIR.glob("PLAN_*.md"):
            try:
                content = f.read_text(encoding="utf-8", errors="replace")
                if re.search(r"^status:\s*(active|in_progress|pending)", content,
                             re.MULTILINE | re.IGNORECASE):
                    count += 1
            except OSError:
                count += 1
        return count

    def _count_plans_created_this_week(self, week_start: date) -> int:
        if not PLANS_DIR.exists():
            return 0
        count = 0
        for f in PLANS_DIR.glob("PLAN_*.md"):
            # Extract date from filename
            date_match = re.search(r"(\d{4}-\d{2}-\d{2})", f.name)
            if date_match:
                try:
                    plan_date = date.fromisoformat(date_match.group(1))
                    if plan_date >= week_start:
                        count += 1
                except ValueError:
                    pass
        return count


# ─────────────────────────────────────────────────────────────────────────────
# INSIGHT GENERATOR
# ─────────────────────────────────────────────────────────────────────────────

class InsightGenerator:
    """Produces human-readable insights and recommendations from WeeklyMetrics."""

    def executive_insights(self, m: WeeklyMetrics) -> list:
        """Return 3-5 bullet-point insights for the executive summary."""
        insights = []

        # Overall throughput
        if m.total_actions > 0:
            insights.append(
                f"AI Employee completed **{m.successful_actions}** of "
                f"**{m.total_actions}** actions with a **{m.success_rate:.0f}%** "
                f"success rate this week."
            )
        else:
            insights.append("No actions logged this week — system may be in first-run state.")

        # Email pipeline
        total_emails = m.emails_processed + m.emails_pending
        if total_emails > 0:
            insights.append(
                f"Email pipeline processed **{m.emails_processed}** of "
                f"**{total_emails}** email tasks "
                f"(**{m.email_process_rate:.0f}%** clearance rate). "
                f"**{m.emails_pending}** items remain pending."
            )

        # Approval workflow
        total_approved = m.approvals_granted + m.approvals_rejected
        if total_approved > 0:
            insights.append(
                f"Human approved **{m.approvals_granted}** of "
                f"**{total_approved}** requests "
                f"(**{m.approval_accept_rate:.0f}%** approval rate)."
            )
        elif m.approvals_pending > 0:
            insights.append(
                f"**{m.approvals_pending}** approval request(s) awaiting human decision."
            )

        # Ralph performance
        if m.ralph_cycles > 0:
            insights.append(
                f"Ralph ran **{m.ralph_cycles}** autonomous cycles and took "
                f"**{m.ralph_actions_taken}** actions "
                f"(**{m.ralph_success_rate:.0f}%** success rate)."
            )
        else:
            insights.append(
                "Ralph autonomous loop has not run yet — "
                "start with `python ralph_wiggum_loop.py`."
            )

        return insights

    def recommendations(self, m: WeeklyMetrics, pending_approvals: list) -> list:
        """Return actionable recommendations for the coming week."""
        recs = []

        # High pending backlog
        if m.emails_pending > 20:
            recs.append(
                f"⚠️  **High email backlog**: {m.emails_pending} items in Needs_Action/. "
                "Consider running `process_emails.bat` or triggering a manual processing cycle."
            )
        elif m.emails_pending > 5:
            recs.append(
                f"📋 **Moderate backlog**: {m.emails_pending} emails pending — "
                "Ralph's next cycle will prioritise these."
            )

        # Expiring approvals
        expiring = self._find_expiring_approvals(pending_approvals)
        if expiring:
            recs.append(
                f"🕐 **Action required**: {len(expiring)} approval(s) expiring within 24 hours:\n"
                + "\n".join(f"   - `{r.filename}`" for r in expiring[:3])
            )

        # Failure rate concern
        if m.success_rate < 80 and m.total_actions > 5:
            recs.append(
                f"🔴 **Success rate below 80%** ({m.success_rate:.0f}%). "
                "Review recent logs for recurring errors."
            )

        # Ralph not running
        if m.ralph_cycles == 0:
            recs.append(
                "🤖 **Start Ralph**: Autonomous loop not active. "
                "Run `python ralph_wiggum_loop.py` for hands-free operation."
            )

        # No failures — positive note
        if m.failed_actions == 0 and m.total_actions > 0:
            recs.append("✅ Zero failures this week — system is healthy.")

        if not recs:
            recs.append("✅ System is operating normally. No immediate actions required.")

        return recs

    def _find_expiring_approvals(self, pending_approvals: list) -> list:
        """Return approvals expiring within 24 hours."""
        soon = []
        now = datetime.utcnow()
        for rec in pending_approvals:
            if rec.outcome != "pending" or not rec.expires:
                continue
            try:
                expires_at = datetime.fromisoformat(rec.expires.rstrip("Z"))
                hours_left = (expires_at - now).total_seconds() / 3600
                if hours_left < 24:
                    soon.append(rec)
            except ValueError:
                pass
        return soon


# ─────────────────────────────────────────────────────────────────────────────
# REPORT BUILDER
# ─────────────────────────────────────────────────────────────────────────────

class ReportBuilder:
    """Assembles the final markdown CEO briefing from all data."""

    def __init__(self, m: WeeklyMetrics, email_tasks: list, approvals: list,
                 ralph_cycles: list, pending_approvals: list, daily_summaries: list):
        self.m = m
        self.email_tasks = email_tasks
        self.approvals = approvals
        self.ralph_cycles = ralph_cycles
        self.pending_approvals = pending_approvals
        self.daily_summaries = daily_summaries
        self.insights = InsightGenerator()
        self.generated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    def build(self) -> str:
        """Return the complete markdown report as a string."""
        sections = [
            self._header(),
            self._section_executive_summary(),
            self._section_key_metrics(),
            self._section_email_analysis(),
            self._section_ralph_analysis(),
            self._section_upcoming_week(),
            self._footer(),
        ]
        return "\n\n".join(sections)

    # ── HEADER ────────────────────────────────────────────────────────────────

    def _header(self) -> str:
        m = self.m
        return f"""---
report_type: ceo_weekly_briefing
week_start: {m.week_start.isoformat()}
week_end: {m.week_end.isoformat()}
generated_at: {self.generated_at}
generated_by: weekly_ceo_briefing.py v{VERSION}
---

# AI Employee — Weekly CEO Briefing

**Week:** {m.week_start.strftime("%B %d")} – {m.week_end.strftime("%B %d, %Y")}
**Generated:** {self.generated_at}
**System:** AI Employee Vault (Gold Tier v{VERSION})

---"""

    # ── SECTION 1: EXECUTIVE SUMMARY ─────────────────────────────────────────

    def _section_executive_summary(self) -> str:
        m = self.m
        exec_insights = self.insights.executive_insights(m)
        insight_lines = "\n".join(f"- {i}" for i in exec_insights)

        return f"""## 1. Executive Summary

### At a Glance

| Category | This Week |
|----------|----------|
| Total Actions | {m.total_actions} |
| Success Rate | {m.success_rate:.0f}% |
| Emails Processed | {m.emails_processed} |
| Emails Pending | {m.emails_pending} |
| Approvals Requested | {m.approvals_requested} |
| Approvals Granted | {m.approvals_granted} |
| Ralph Autonomous Cycles | {m.ralph_cycles} |
| Plans Active | {m.plans_active} |

### Key Insights

{insight_lines}"""

    # ── SECTION 2: KEY METRICS ────────────────────────────────────────────────

    def _section_key_metrics(self) -> str:
        m = self.m

        # Build daily breakdown table
        daily_rows = []
        for summary in self.daily_summaries:
            day_name = summary.date.strftime("%a %d %b")
            bar = self._mini_bar(summary.successful, summary.total_actions)
            daily_rows.append(
                f"| {day_name} | {summary.total_actions} | "
                f"{summary.successful} | {summary.failed} | {bar} |"
            )
        daily_table = (
            "| Day | Actions | ✓ | ✗ | Success |\n"
            "|-----|---------|---|---|--------|\n"
            + ("\n".join(daily_rows) if daily_rows else "| *No data* | — | — | — | — |")
        )

        # Action type breakdown
        action_rows = []
        for action_type, count in m.action_types.most_common(8):
            action_rows.append(f"| `{action_type}` | {count} |")
        action_table = (
            "| Action Type | Count |\n"
            "|-------------|-------|\n"
            + ("\n".join(action_rows) if action_rows else "| *none* | 0 |")
        )

        return f"""## 2. Key Metrics

### Processing Performance

| Metric | Value |
|--------|-------|
| Total Actions | {m.total_actions} |
| Successful | {m.successful_actions} ({m.success_rate:.0f}%) |
| Failed | {m.failed_actions} |
| Files Processed | {m.files_processed} |
| Files Created | {m.files_created} |
| Approval Accept Rate | {m.approval_accept_rate:.0f}% |

### Daily Breakdown

{daily_table}

### Action Type Breakdown

{action_table}"""

    # ── SECTION 3: EMAIL ANALYSIS ─────────────────────────────────────────────

    def _section_email_analysis(self) -> str:
        m = self.m

        # Top senders table (top 10)
        sender_rows = []
        for sender, count in m.email_senders.most_common(10):
            pct = count / max(len(self.email_tasks), 1) * 100
            sender_rows.append(f"| {sender[:45]} | {count} | {pct:.0f}% |")
        sender_table = (
            "| Sender | Emails | % of Total |\n"
            "|--------|--------|----------|\n"
            + ("\n".join(sender_rows) if sender_rows else "| *No email data* | — | — |")
        )

        # Top domains table (top 8)
        domain_rows = []
        for domain, count in m.email_domains.most_common(8):
            domain_rows.append(f"| `{domain}` | {count} |")
        domain_table = (
            "| Domain | Count |\n"
            "|--------|-------|\n"
            + ("\n".join(domain_rows) if domain_rows else "| *No data* | — |")
        )

        # Priority breakdown
        high_count = m.email_priorities.get("high", 0)
        normal_count = m.email_priorities.get("normal", 0)
        low_count = m.email_priorities.get("low", 0)
        total_pri = high_count + normal_count + low_count or 1

        return f"""## 3. Email Analysis

### Volume Summary

| Metric | Count |
|--------|-------|
| Emails This Week | {m.emails_received} |
| Processed → Done | {m.emails_processed} |
| Still Pending | {m.emails_pending} |
| Clearance Rate | {m.email_process_rate:.0f}% |

### Priority Breakdown

| Priority | Count | % |
|----------|-------|----|
| 🔴 High | {high_count} | {high_count/total_pri*100:.0f}% |
| 🟡 Normal | {normal_count} | {normal_count/total_pri*100:.0f}% |
| 🟢 Low | {low_count} | {low_count/total_pri*100:.0f}% |

### Top Senders

{sender_table}

### Top Sending Domains

{domain_table}"""

    # ── SECTION 4: RALPH ANALYSIS ─────────────────────────────────────────────

    def _section_ralph_analysis(self) -> str:
        m = self.m

        # Ralph action breakdown
        ralph_action_rows = []
        for action_name, count in m.ralph_action_types.most_common():
            ralph_action_rows.append(f"| `{action_name}` | {count} |")
        ralph_table = (
            "| Action | Times Executed |\n"
            "|--------|---------------|\n"
            + ("\n".join(ralph_action_rows) if ralph_action_rows
               else "| *No autonomous actions yet* | — |")
        )

        # Recent cycles (last 5)
        recent_cycles = self.ralph_cycles[-5:] if self.ralph_cycles else []
        cycle_rows = []
        for c in reversed(recent_cycles):
            actions_str = ", ".join(
                f"{'✓' if s else '✗'} {n}" for n, s, _ in c.actions[:3]
            ) or "— (no actions)"
            cycle_rows.append(
                f"| #{c.cycle_num} | {c.timestamp[:16]} | {c.context} | "
                f"{c.pending_count} | {actions_str} |"
            )
        cycle_table = (
            "| Cycle | Time | Context | Pending | Actions |\n"
            "|-------|------|---------|---------|--------|\n"
            + ("\n".join(cycle_rows) if cycle_rows
               else "| *No cycle data yet* | — | — | — | — |")
        )

        status = "🟢 Active" if m.ralph_cycles > 0 else "⚪ Not started"

        return f"""## 4. Ralph Autonomous Actions

### Overview

| Metric | Value |
|--------|-------|
| Status | {status} |
| Total Cycles Run | {m.ralph_cycles} |
| Total Actions Taken | {m.ralph_actions_taken} |
| Successful Actions | {m.ralph_actions_succeeded} |
| Failed Actions | {m.ralph_actions_failed} |
| Autonomous Success Rate | {m.ralph_success_rate:.0f}% |

### Action Breakdown

{ralph_table}

### Recent Cycles

{cycle_table}

### Notes

{"Ralph has been running autonomously and managing the vault without manual intervention." if m.ralph_cycles > 0 else "Ralph has not yet started. Run `python ralph_wiggum_loop.py` to enable Gold tier autonomy."}"""

    # ── SECTION 5: UPCOMING WEEK PREVIEW ─────────────────────────────────────

    def _section_upcoming_week(self) -> str:
        m = self.m
        next_week_start = m.week_end + timedelta(days=1)
        next_week_end = m.week_end + timedelta(days=7)

        # Pending approvals detail
        approval_rows = []
        for rec in self.pending_approvals:
            if rec.outcome == "pending":
                expires_str = rec.expires[:10] if rec.expires else "unknown"
                approval_rows.append(
                    f"| `{rec.filename[:50]}` | {rec.risk_level} | {expires_str} |"
                )
        approval_table = (
            "| Approval File | Risk | Expires |\n"
            "|---------------|------|--------|\n"
            + ("\n".join(approval_rows) if approval_rows
               else "| *No pending approvals* | — | — |")
        )

        # Top pending emails
        top_pending = [e for e in self.email_tasks
                       if e.folder == "Needs_Action" and e.priority == "high"][:5]
        pending_rows = []
        for info in top_pending:
            pending_rows.append(f"| `{info.filename[:55]}` | {info.priority} |")
        if m.emails_pending > len(top_pending):
            pending_rows.append(
                f"| *… and {m.emails_pending - len(top_pending)} more* | — |"
            )
        pending_table = (
            "| File | Priority |\n"
            "|------|----------|\n"
            + ("\n".join(pending_rows) if pending_rows
               else "| *No high-priority pending items* | — |")
        )

        # Recommendations
        recs = self.insights.recommendations(m, self.pending_approvals)
        rec_lines = "\n".join(f"- {r}" for r in recs)

        return f"""## 5. Upcoming Week Preview

**Period:** {next_week_start.strftime("%B %d")} – {next_week_end.strftime("%B %d, %Y")}

### Pending Approvals Requiring Human Decision

{approval_table}

### High-Priority Pending Items

{pending_table}

### Recommendations

{rec_lines}

### Scheduled Automation

| Task | Schedule | Script |
|------|----------|--------|
| Morning Briefing | 8:00 AM daily | `scheduled_tasks/morning_briefing.bat` |
| Email Processing | Every 2 hours | `scheduled_tasks/process_emails.bat` |
| Evening Summary | 8:00 PM daily | `scheduled_tasks/daily_summary.bat` |
| CEO Briefing | Sundays | `python weekly_ceo_briefing.py` |
| Ralph Loop | Continuous | `python ralph_wiggum_loop.py` |"""

    # ── FOOTER ────────────────────────────────────────────────────────────────

    def _footer(self) -> str:
        return f"""---

*Generated by AI Employee — Gold Tier CEO Briefing Skill v{VERSION}*
*Report period: {self.m.week_start.isoformat()} to {self.m.week_end.isoformat()}*
*Next briefing: {(self.m.week_end + timedelta(days=7)).isoformat()} (Sunday)*"""

    # ── HELPERS ───────────────────────────────────────────────────────────────

    def _mini_bar(self, success: int, total: int, width: int = 8) -> str:
        """Return a mini ASCII progress bar like '████░░░░ 75%'."""
        if total == 0:
            return "—"
        ratio = success / total
        filled = round(ratio * width)
        bar = "█" * filled + "░" * (width - filled)
        return f"`{bar}` {ratio*100:.0f}%"


# ─────────────────────────────────────────────────────────────────────────────
# ORCHESTRATOR
# ─────────────────────────────────────────────────────────────────────────────

class CEOBriefingGenerator:
    """Top-level orchestrator: gather all data → aggregate → build → save."""

    def __init__(self, week_end: date, days: int = 7, stdout: bool = False):
        self.week_end = week_end
        self.days = days
        self.stdout = stdout

    def run(self) -> Path:
        """Generate the briefing and return the output file path."""
        print(f"AI Employee — Weekly CEO Briefing")
        print(f"Week ending : {self.week_end.isoformat()}")
        print(f"Lookback    : {self.days} days")
        print(f"Vault       : {VAULT_ROOT}")
        print()

        # ── Step 1: Parse all data sources ───────────────────────────────────
        print("Parsing daily logs...")
        daily_summaries = DailyLogParser().parse_week(self.week_end, self.days)
        print(f"  Found {len(daily_summaries)} daily log file(s)")

        print("Scanning email task files...")
        email_parser = EmailTaskParser()
        email_tasks = (
            email_parser.scan_folder(NEEDS_ACTION_DIR, "Needs_Action") +
            email_parser.scan_folder(DONE_DIR, "Done")
        )
        print(f"  Found {len(email_tasks)} email task file(s)")

        print("Scanning approval records...")
        approval_parser = ApprovalParser()
        approvals = (
            approval_parser.scan_folder(DONE_DIR, "Done") +
            approval_parser.scan_folder(PENDING_APPROVAL_DIR, "Pending_Approval") +
            approval_parser.scan_folder(APPROVED_DIR, "Approved") +
            approval_parser.scan_folder(REJECTED_DIR, "Rejected")
        )
        pending_approvals = [a for a in approvals if a.outcome == "pending"]
        print(f"  Found {len(approvals)} approval record(s) ({len(pending_approvals)} pending)")

        print("Parsing Ralph autonomous logs...")
        ralph_cycles = RalphLogParser().parse_week(self.week_end, self.days)
        print(f"  Found {len(ralph_cycles)} Ralph cycle(s)")

        # ── Step 2: Aggregate metrics ─────────────────────────────────────────
        print("Aggregating metrics...")
        metrics = MetricsAggregator().aggregate(
            week_end=self.week_end,
            days=self.days,
            daily_summaries=daily_summaries,
            email_tasks=email_tasks,
            approvals=approvals,
            ralph_cycles=ralph_cycles,
        )

        # ── Step 3: Build report ──────────────────────────────────────────────
        print("Building report...")
        builder = ReportBuilder(
            m=metrics,
            email_tasks=email_tasks,
            approvals=approvals,
            ralph_cycles=ralph_cycles,
            pending_approvals=pending_approvals,
            daily_summaries=daily_summaries,
        )
        report_md = builder.build()

        # ── Step 4: Output ────────────────────────────────────────────────────
        if self.stdout:
            print("\n" + "=" * 70)
            print(report_md)
            return Path("/dev/stdout")

        REPORTS_DIR.mkdir(parents=True, exist_ok=True)
        output_file = REPORTS_DIR / f"CEO_Briefing_{self.week_end.isoformat()}.md"
        output_file.write_text(report_md, encoding="utf-8")
        print(f"\nReport saved: {output_file}")
        print(f"  Size: {len(report_md):,} characters")

        return output_file


# ─────────────────────────────────────────────────────────────────────────────
# ENTRY POINT
# ─────────────────────────────────────────────────────────────────────────────

def last_sunday(from_date: date) -> date:
    """Return the most recent Sunday on or before from_date."""
    days_since_sunday = (from_date.weekday() + 1) % 7  # Monday=0, Sunday=6
    return from_date - timedelta(days=days_since_sunday)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="AI Employee — Weekly CEO Briefing Generator (Gold Tier)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python weekly_ceo_briefing.py                         # Last 7 days ending today
  python weekly_ceo_briefing.py --date 2026-02-23       # Week ending Feb 23
  python weekly_ceo_briefing.py --days 14               # Bi-weekly report
  python weekly_ceo_briefing.py --stdout                 # Print to console
  python weekly_ceo_briefing.py --date 2026-02-23 --stdout
        """,
    )
    parser.add_argument(
        "--date",
        help="Week-end date in YYYY-MM-DD format (default: today)",
        default=None,
    )
    parser.add_argument(
        "--days",
        type=int,
        default=7,
        help="Number of days to look back (default: 7)",
    )
    parser.add_argument(
        "--stdout",
        action="store_true",
        help="Print report to stdout instead of saving to Reports/",
    )

    args = parser.parse_args()

    # Resolve the week-end date
    if args.date:
        try:
            week_end = date.fromisoformat(args.date)
        except ValueError:
            print(f"Error: invalid date '{args.date}'. Use YYYY-MM-DD format.")
            sys.exit(1)
    else:
        week_end = date.today()

    generator = CEOBriefingGenerator(
        week_end=week_end,
        days=args.days,
        stdout=args.stdout,
    )
    generator.run()


if __name__ == "__main__":
    main()
