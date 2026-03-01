# Personal AI Employee — Gold Tier Submission

**Hackathon Submission | February 2026 | Esha Khan**

> A local-first autonomous AI employee that monitors emails, processes tasks, manages approvals, posts to social media, briefs executives, and integrates personal and business domains — all with human-in-the-loop safety gates.

---

## 🏆 Achievement Summary

| Metric | Value |
|--------|-------|
| **Tier** | Gold (9/10 requirements) |
| **Time Invested** | 40+ hours |
| **Total Files** | 150+ |
| **MCP Servers** | 5 |
| **MCP Tools** | 29 |
| **Agent Skills** | 10 |
| **Social Platforms** | 4 (LinkedIn · Twitter · Instagram · Facebook) |
| **Autonomous Cycles** | 8+ (Ralph OODA loop) |
| **CEO Briefings Generated** | 2 |
| **Tasks Completed** | 117+ |
| **Real Emails Sent** | 2 (verified msg IDs) |

---

## ✅ Requirements Completed

### 🥉 Bronze Tier — All Complete

- ✅ **Structured Vault** — 9-folder lifecycle management system (`Needs_Action/` → `Done/`)
- ✅ **Company Handbook** — `Company_Handbook.md` with rules, thresholds, and safety policies
- ✅ **Live Dashboard** — `Dashboard.md` with real-time status, activity feed, system health
- ✅ **Filesystem Watcher** — `filesystem_watcher.py` monitors `DropFolder/` with `watchdog`
- ✅ **File Processing Workflow** — Detect → Read → Analyse → Act → Update → Move → Log
- ✅ **Priority Detection** — Emergency keyword scanning (urgent, asap, critical, deadline, etc.)
- ✅ **Agent Skills** — Modular skill definitions: `FILE_PROCESSOR_SKILL`, `DASHBOARD_UPDATER_SKILL`, `LOGGER_SKILL`
- ✅ **Audit Logging** — Structured ISO 8601 daily logs in `Logs/YYYY-MM-DD.md`
- ✅ **Safety Rules** — Never delete, always log, always approve external actions

### 🥈 Silver Tier — All Complete

- ✅ **HITL Approval Workflow** — Full lifecycle: `Pending_Approval/` → `Approved/`|`Rejected/` → `Done/`
- ✅ **Gmail Watcher** — `gmail_watcher.py` polls inbox every 5 min, creates `EMAIL_*.md` task files
- ✅ **Email MCP Server** — `mcp_servers/email_mcp/` Node.js server with `send_email` tool (Gmail OAuth)
- ✅ **Live Email Verified** — 2 real emails sent to esha7392@gmail.com (msg IDs: `19c6e84d3e1e419d`, `19c6e9c0ac712f6b`)
- ✅ **Task Scheduler Automation** — Windows `.bat` wrappers for Ralph, Gmail, CEO Briefing, Social Media
- ✅ **Planning Skill** — `PLAN_CREATOR_SKILL` with tracked multi-step plans in `Plans/`
- ✅ **OAuth 2.0 Integration** — Shared token auto-refresh between Python and Node.js components

### 🥇 Gold Tier — 9/10 Complete

- ✅ **Ralph Wiggum Autonomous Loop** — `ralph_wiggum_loop.py` with full OODA cycle (8+ iterations, 0 errors)
- ✅ **Social Media Auto-Poster** — `social_media_auto_poster.py` v3.0 — 4 platforms, HITL-gated, content rotation
- ✅ **Social Media MCP Server** — `mcp_servers/social_media_mcp/` — 12 tools across LinkedIn, Twitter, Instagram, Facebook
- ✅ **File Operations MCP Server** — `mcp_servers/file_ops_mcp/` — 5 tools for vault filesystem operations
- ✅ **Weekly CEO Briefing** — `weekly_ceo_briefing.py` — 5-section markdown reports in `Reports/`
- ✅ **Google Workspace Integration** — `mcp_servers/google_workspace_mcp/` — 6 tools (Calendar + Drive + Business Gmail)
- ✅ **Slack Team Communication** — `mcp_servers/slack_mcp/` — 5 tools (messages, DMs, files, mentions, reminders)
- ✅ **Cross-Domain Integration** — `cross_domain_integration_demo.py` — 3 workflows bridging personal + business domains
- ✅ **10 Agent Skills Documented** — Full skill library covering all system capabilities
- ❌ **Odoo ERP Integration** — Not implemented (deprioritised in favour of broader cross-domain coverage)

---

## 🎯 Key Features

### Ralph Wiggum — Autonomous OODA Loop

Ralph is the Gold-tier autonomous agent that runs continuously, making decisions without human prompting. It implements a full **Observe → Orient → Decide → Act → Reflect** cycle:

- Monitors `Needs_Action/`, `Pending_Approval/`, `Approved/`, and system state
- Prioritises urgent emails, expiring approvals, and high-impact actions
- Creates plans before multi-step workflows
- Logs every decision to `Logs/` and updates `Dashboard.md`
- Completed **8+ autonomous cycles** with 0 errors in testing

### Cross-Domain Integration (Personal ↔ Business)

The crown jewel of the Gold tier — three end-to-end workflows that bridge personal and business systems:

| Workflow | Trigger | Action |
|----------|---------|--------|
| **1. Email → Business** | Urgent personal email | Creates Calendar event + Slack alert + Drive upload |
| **2. Calendar → Personal** | Upcoming business meeting | Sends personal reminder + Slack reminder to team lead |
| **3. CEO Briefing Distribution** | Weekly report generated | Uploads to Drive + Posts to Slack + Schedules review meeting |

All cross-domain write actions create HITL approval files before touching external systems.

### 5 MCP Servers, 29 Tools

```
email_mcp          (1 tool)  — send_email via Gmail API
file_ops_mcp       (5 tools) — search, read, summarise, organise, analyse
social_media_mcp  (12 tools) — LinkedIn, Twitter, Instagram, Facebook
google_workspace_mcp (6 tools) — Calendar, Drive, Business Gmail
slack_mcp          (5 tools) — messages, DMs, files, mentions, reminders
```

### Social Media Auto-Poster (4 Platforms)

Generates platform-specific content with quality gates, scheduling, and approval workflow:
- **Content types:** achievement · thought_leadership · tip · behind_the_scenes
- **Quality gates:** character limits, hashtag counts, CTA checks per platform
- **Rotation:** avoids repeating the same content type in last 3 posts
- **Cadence:** Monday / Wednesday / Friday at 10:00 AM

### HITL Safety Model

Every external action is gated behind human approval:

```
AI decides to act
      │
      ▼
Creates Pending_Approval/ACTION_*.md
      │
      ▼ (human reviews)
  ┌───┴───┐
  ▼       ▼
Approved/ Rejected/
  │
  ▼
MCP executes → Done/ (audit trail)
```

**Read operations** execute immediately. **Write operations** always wait for human approval.

---

## 🏗️ Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│                        PERSONAL DOMAIN                           │
│                                                                  │
│  Personal Gmail                   Local Filesystem              │
│  gmail_watcher.py ──────────────► filesystem_watcher.py         │
│  EMAIL_*.md → Needs_Action/       DropFolder/ → Needs_Action/   │
└────────────────────────┬─────────────────────────────────────────┘
                         │
                         ▼
┌──────────────────────────────────────────────────────────────────┐
│              RALPH WIGGUM — AUTONOMOUS OODA LOOP                 │
│                                                                  │
│   OBSERVE ──► ORIENT ──► DECIDE ──► ACT ──► REFLECT ──► (loop)  │
│                                                                  │
│   Priority Queue:                                                │
│   1. Urgent emails          5. Normal emails                     │
│   2. Expiring approvals     6. Cross-domain workflows            │
│   3. Social media posts     7. CEO briefing                      │
│   4. Dashboard update       8. System health check               │
└────────────────────────┬─────────────────────────────────────────┘
                         │ All writes → Pending_Approval/ (HITL)
                         ▼
┌──────────────────────────────────────────────────────────────────┐
│                    5 MCP SERVERS (29 tools)                      │
│                                                                  │
│  ┌─────────────┐  ┌─────────────┐  ┌──────────────────────────┐ │
│  │ email_mcp   │  │ file_ops_mcp│  │   social_media_mcp       │ │
│  │ 1 tool      │  │ 5 tools     │  │   12 tools               │ │
│  │ send_email  │  │ search      │  │   LinkedIn  Twitter      │ │
│  │             │  │ read        │  │   Instagram Facebook     │ │
│  │             │  │ summarise   │  │   cross_post + more      │ │
│  │             │  │ organise    │  └──────────────────────────┘ │
│  │             │  │ analyse     │                               │ │
│  └─────────────┘  └─────────────┘  ┌──────────────────────────┐ │
│                                    │  google_workspace_mcp    │ │
│                                    │  6 tools                 │ │
│  ┌─────────────────────────────┐   │  calendar_list_events    │ │
│  │        slack_mcp            │   │  calendar_create_event   │ │
│  │        5 tools              │   │  drive_search_files      │ │
│  │  send_channel_message       │   │  drive_upload_file       │ │
│  │  send_dm                    │   │  drive_share_file        │ │
│  │  post_file                  │   │  gmail_business_search   │ │
│  │  get_mentions               │   └──────────────────────────┘ │
│  │  create_reminder            │                                │ │
│  └─────────────────────────────┘                                │ │
└────────────────────────┬─────────────────────────────────────────┘
                         │
                         ▼
┌──────────────────────────────────────────────────────────────────┐
│                       BUSINESS DOMAIN                            │
│                                                                  │
│  Google Calendar ──► Meeting scheduling & reminders             │
│  Google Drive    ──► Document storage, upload & sharing         │
│  Business Gmail  ──► Professional email search & context        │
│  Slack           ──► Team notifications, DMs & file sharing     │
│  Social Media    ──► LinkedIn, Twitter, Instagram, Facebook     │
└──────────────────────────────────────────────────────────────────┘
```

### Tech Stack

| Layer | Technology |
|-------|-----------|
| AI Engine | Claude Code (claude-sonnet-4-6) |
| Scripting | Python 3.11 |
| MCP Servers | Node.js 18 + `@modelcontextprotocol/sdk` |
| Email / OAuth | Gmail API v1, Google OAuth 2.0 |
| Workspace | Google Calendar API v3, Google Drive API v3 |
| Team Comms | Slack Web API |
| Social Media | LinkedIn, Twitter, Instagram, Facebook APIs (simulation) |
| Filesystem | `watchdog` (Python) |
| Vault Format | Markdown files (human-readable, git-trackable) |
| Scheduling | Windows Task Scheduler + `.bat` wrappers |
| Visualisation | Obsidian |

---

## 📁 File Structure

```
AI_Employee_Vault/
│
├── Dashboard.md                      # Live system status + activity feed
├── Company_Handbook.md               # AI policy, rules, approval thresholds
├── README.md                         # This file
│
├── filesystem_watcher.py             # Bronze: monitors DropFolder/
├── gmail_watcher.py                  # Silver: polls Gmail every 5 min
├── ralph_wiggum_loop.py              # Gold: autonomous OODA loop
├── weekly_ceo_briefing.py            # Gold: weekly executive reports
├── social_media_auto_poster.py       # Gold: 4-platform social posting (v3.0)
├── cross_domain_integration_demo.py  # Gold: 3 cross-domain workflows
│
├── ralph_config.json                 # Ralph's priority queue + settings
├── ralph_state.json                  # Persistent loop state (8+ cycles)
├── social_media_post_history.json    # Post history for content rotation
├── credentials.json                  # Google OAuth credentials (gitignored)
├── token.json                        # OAuth token with auto-refresh (gitignored)
├── requirements.txt                  # Python deps: watchdog, google-auth, etc.
│
├── mcp_servers/
│   ├── email_mcp/                    # Silver: 1 tool — send_email
│   │   ├── index.js
│   │   ├── package.json
│   │   └── README.md
│   ├── file_ops_mcp/                 # Gold: 5 tools — vault filesystem ops
│   │   ├── index.js
│   │   ├── package.json
│   │   └── README.md
│   ├── social_media_mcp/             # Gold: 12 tools — 4 platforms
│   │   ├── index.js
│   │   ├── package.json
│   │   └── README.md
│   ├── google_workspace_mcp/         # Gold: 6 tools — Calendar+Drive+Gmail Biz
│   │   ├── index.js
│   │   ├── package.json
│   │   └── README.md
│   └── slack_mcp/                    # Gold: 5 tools — team communication
│       ├── index.js
│       ├── package.json
│       └── README.md
│
├── Skills/                           # 10 agent skill definitions
│   ├── FILE_PROCESSOR_SKILL.md       # Bronze
│   ├── DASHBOARD_UPDATER_SKILL.md    # Bronze
│   ├── LOGGER_SKILL.md               # Bronze
│   ├── HITL_APPROVAL_SKILL.md        # Silver
│   ├── PLAN_CREATOR_SKILL.md         # Silver
│   ├── RALPH_WIGGUM_SKILL.md         # Gold
│   ├── WEEKLY_CEO_BRIEFING_SKILL.md  # Gold
│   ├── EMAIL_WATCHER_SKILL.md        # Gold
│   ├── SOCIAL_MEDIA_AUTOPOSTER_SKILL.md # Gold
│   └── CROSS_DOMAIN_INTEGRATION_SKILL.md # Gold
│
├── Plans/                            # Multi-step workflow plans
├── Reports/                          # Weekly CEO briefings
├── Needs_Action/                     # Incoming tasks (EMAIL_*.md, FILE_*.md)
├── Done/                             # 117+ completed tasks + resolved approvals
├── Logs/                             # Daily audit logs (Logs/YYYY-MM-DD.md)
├── Pending_Approval/                 # HITL queue — awaiting human decision
├── Approved/                         # Approved actions (transient)
└── Rejected/                         # Rejected actions (transient)
```

---

## 🚀 Demo Instructions

### Prerequisites

```bash
# Python 3.8+
pip install -r requirements.txt

# Node.js 18+
cd mcp_servers/email_mcp && npm install
cd mcp_servers/file_ops_mcp && npm install
cd mcp_servers/social_media_mcp && npm install
cd mcp_servers/google_workspace_mcp && npm install
cd mcp_servers/slack_mcp && npm install

# Claude Code CLI
npm install -g @anthropic-ai/claude-code
```

### Demo 1: Ralph Wiggum Autonomous Loop

```bash
# Start the autonomous agent (runs OODA cycles continuously)
python ralph_wiggum_loop.py

# Ralph will:
# 1. Observe — scan Needs_Action/, Pending_Approval/, Approved/
# 2. Orient  — classify urgency, check for expiring approvals
# 3. Decide  — build priority-ordered action plan
# 4. Act     — process emails, create approval requests
# 5. Reflect — log decisions, update Dashboard.md
# 6. Sleep   — wait 5 minutes, repeat

# Check Ralph's state
cat ralph_state.json
```

### Demo 2: Gmail Watcher

```bash
# Poll inbox and convert emails to task files
python gmail_watcher.py

# Output: EMAIL_*.md files in Needs_Action/
# Priority labels: URGENT / HIGH / NORMAL / PROMOTIONAL
```

### Demo 3: Weekly CEO Briefing

```bash
# Generate the executive briefing report
python weekly_ceo_briefing.py

# Output: Reports/CEO_Briefing_YYYY-MM-DD.md
# Sections: Executive Summary, Email Intelligence, Task Metrics,
#           System Performance, Priority Actions
```

### Demo 4: Social Media Posting (4 Platforms)

```bash
# Check status of all platforms
python social_media_auto_poster.py --status

# Generate a post for all platforms (dry-run — no files created)
python social_media_auto_poster.py --generate --platform all --dry-run

# Generate a LinkedIn post (creates approval file)
python social_media_auto_poster.py --generate --platform linkedin

# Approve a post (move approval file to Approved/ then run):
python social_media_auto_poster.py --check-approved
```

### Demo 5: Cross-Domain Integration (3 Workflows)

```bash
# Dry-run all 3 cross-domain workflows
python cross_domain_integration_demo.py --workflow all --dry-run

# Run a specific workflow (creates real approval files)
python cross_domain_integration_demo.py --workflow 1  # Email → Calendar + Slack + Drive
python cross_domain_integration_demo.py --workflow 2  # Calendar → Personal reminder
python cross_domain_integration_demo.py --workflow 3  # CEO Briefing → Drive + Slack + Calendar
```

### Demo 6: HITL Approval Workflow

```bash
# Have Claude create an approval request
claude "Draft a professional email to the team about the project status and request approval to send"

# Review the approval file in Pending_Approval/
# Move it to Approved/ to execute, or Rejected/ to cancel

# Check and execute all approved actions
claude "Check Approved folder and execute all pending approvals using HITL_APPROVAL_SKILL"
```

### Demo 7: All MCP Tools via Claude Code

```bash
# Use any of the 29 MCP tools directly
claude "Use file_ops_mcp to search for all CEO briefing reports"
claude "Use social_media_mcp to generate a LinkedIn post about our AI automation progress"
claude "Use google_workspace_mcp to list my upcoming calendar events for this week"
claude "Use slack_mcp to get recent mentions of the AI Employee bot"
```

---

## 📊 Evidence

### File Counts

| Directory | Count | Description |
|-----------|-------|-------------|
| `Done/` | 117+ | Completed tasks + archived approvals |
| `Logs/` | 4 | Daily audit log files |
| `Reports/` | 2 | CEO briefing reports |
| `Plans/` | 2+ | Multi-step workflow plans |
| `Skills/` | 10 | Agent skill documents |
| `mcp_servers/` | 5 | MCP server directories |

### Autonomous Activity

| Metric | Value |
|--------|-------|
| Ralph OODA cycles | 8+ |
| Ralph errors | 0 |
| Emails processed | 110+ |
| Approvals processed | 3 |
| CEO briefings generated | 2 |
| Social media posts drafted | All 4 platforms tested |
| Cross-domain workflows | 3 (all dry-run verified) |

### Live Test Results

| Test | Result | Evidence |
|------|--------|---------|
| Email send #1 | ✅ Delivered | msg_id: `19c6e84d3e1e419d` |
| Email send #2 | ✅ Delivered | msg_id: `19c6e9c0ac712f6b` |
| Ralph cycle #1-8 | ✅ 0 errors | `ralph_state.json` |
| CEO briefing | ✅ Generated | `Reports/CEO_Briefing_*.md` |
| Social media (all platforms) | ✅ Approval files created | `Pending_Approval/` |
| Cross-domain dry-run | ✅ 9 MCP calls, 9 approval files | Console output |

### Log Locations

```
Logs/2026-02-15.md    # Bronze/Silver activity
Logs/2026-02-17.md    # Email batch processing (110 files)
Logs/2026-02-18.md    # Gmail watcher + HITL approvals
Logs/2026-02-28.md    # Gold tier autonomous activity
```

### Key State Files

```bash
cat ralph_state.json                  # 8 cycles, timestamps, last actions
cat social_media_post_history.json   # v3.0, all 4 platforms
cat Dashboard.md                     # Live Gold v3.0 system status
cat FINAL_GOLD_VERIFICATION.md       # 25/25 evidence checks
cat SKILLS_AUDIT.md                  # Full skills audit report
```

---

## 🏗️ Design Decisions

### 1. File-First Architecture
Every component communicates through markdown files. No internal databases or APIs between components. This makes the entire system **human-readable**, git-trackable, and debuggable by opening a folder in Obsidian.

### 2. Skills as Markdown
Agent behaviours are defined as structured `.md` files that Claude reads as instructions. This means capabilities are easy to update, version, audit, and extend without touching code.

### 3. Safety by Default
"Never delete, always log, always approve external actions" — encoded in `Company_Handbook.md` and enforced by `HITL_APPROVAL_SKILL`. **All 5 MCP servers default to SIMULATION MODE** — no credentials required to explore the system.

### 4. Simulation-First MCP Design
Each MCP server has boolean simulation flags (`SIMULATE_*`). Flipping them to `false` and setting the corresponding environment variables activates live API calls. This means the entire system can be demoed without any credentials.

### 5. Separation of Concerns
- Personal Gmail token ≠ Business Gmail token
- Each MCP server is independently deployable
- Ralph's config lives in `ralph_config.json`, separate from loop logic

---

## 🙏 Acknowledgments

**Hackathon Organiser:** Thank you for an ambitious brief that pushed the boundaries of what a "personal AI employee" can mean. The tiered structure was a brilliant framework for progressive capability building.

**Technologies:**
- [Claude Code](https://docs.anthropic.com/claude-code) — the AI engine that reads Skills, calls MCP tools, and makes all decisions
- [Model Context Protocol](https://modelcontextprotocol.io) — the open standard that lets Claude talk to custom tool servers
- [Google APIs](https://developers.google.com) — Gmail, Calendar, Drive OAuth 2.0 integrations
- [Slack API](https://api.slack.com) — team communication layer
- [Obsidian](https://obsidian.md) — vault visualisation (the system works without it, but it makes it beautiful)
- [watchdog](https://pypi.org/project/watchdog/) — Python filesystem monitoring

---

## 📋 Quick Start (Minimal Setup)

```bash
# 1. Clone and install
git clone <repo>
pip install -r requirements.txt
cd mcp_servers/email_mcp && npm install && cd ../..

# 2. Set up Gmail OAuth (for email features)
# - Follow mcp_servers/email_mcp/README.md
# - Creates credentials.json + token.json

# 3. Start Claude Code with MCP servers
claude  # .claude/mcp_config.json auto-loads all 5 servers

# 4. Run your first autonomous cycle
python ralph_wiggum_loop.py

# 5. Or demo everything with zero credentials (simulation mode)
python cross_domain_integration_demo.py --workflow all --dry-run
python social_media_auto_poster.py --generate --platform all --dry-run
python weekly_ceo_briefing.py
```

---

*Built with Claude Code | Gold Tier v3.0 | February 2026*
*5 MCP servers · 29 tools · 10 skills · 4 social platforms · 3 cross-domain workflows*
