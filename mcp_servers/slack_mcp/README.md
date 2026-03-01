# Slack MCP Server

MCP server providing Claude Code with access to Slack team communication.

**Status:** SIMULATION MODE (default) — flip flag + set bot token to go live
**Tools:** 5
**Version:** 1.0.0

---

## Tools

| Tool | Action | Requires Approval |
|------|--------|-------------------|
| `send_channel_message` | Post to a public/private channel | Yes |
| `send_dm` | Send a direct message | Yes |
| `post_file` | Upload a file to a channel | Yes |
| `get_mentions` | Fetch bot mentions (read-only) | No |
| `create_reminder` | Set a Slack reminder | Yes |

---

## Setup

### 1. Create a Slack App

1. Go to [api.slack.com/apps](https://api.slack.com/apps)
2. Click **Create New App → From scratch**
3. Name it `AI Employee` and choose your workspace

### 2. Configure Bot Scopes

Go to **OAuth & Permissions → Bot Token Scopes** and add:

| Scope | Purpose |
|-------|---------|
| `chat:write` | Send channel messages |
| `im:write` | Send DMs |
| `files:write` | Upload files |
| `search:read` | Get bot mentions |
| `reminders:write` | Create reminders |
| `channels:read` | List channels |
| `users:read` | Look up user IDs for DMs |

### 3. Install the App to Your Workspace

1. Go to **OAuth & Permissions → Install to Workspace**
2. Copy the **Bot User OAuth Token** (`xoxb-...`)

### 4. Set Environment Variables

```bash
# Windows
set SLACK_BOT_TOKEN=xoxb-your-bot-token
set SLACK_TEAM_ID=T0123456789
set SLACK_BOT_USER_ID=U0123456789
set SLACK_DEFAULT_CHANNEL=#general
set SLACK_TEAM_CHANNEL=#ai-employee

# Linux/macOS
export SLACK_BOT_TOKEN=xoxb-...
```

To find your Team ID and Bot User ID:
```bash
# Team ID — visible in workspace URL: https://app.slack.com/client/T0123456789/...
# Bot User ID — from api.slack.com/apps → your app → Basic Information
```

### 5. Enable Live Mode

Edit `mcp_servers/slack_mcp/index.js`:

```javascript
// Change from true to false:
const SIMULATE_SLACK = false;
```

### 6. Invite the Bot to Channels

In Slack, `/invite @AI Employee` to any channel the bot needs to post in.

### 7. Install & Test

```bash
cd mcp_servers/slack_mcp
npm install
node index.js
# Should print: Slack MCP Server running on stdio
```

---

## API Reference

### `send_channel_message`

Posts a message to a Slack channel. Requires human approval (HITL).

**Input:**
| Parameter | Type | Required | Default |
|-----------|------|----------|---------|
| `channel` | string | No | `SLACK_DEFAULT_CHANNEL` |
| `message` | string | Yes | — |
| `thread_ts` | string | No | — |

**Creates:** `Pending_Approval/SLACK_MESSAGE_{id}_{date}.md`

---

### `send_dm`

Sends a direct message to a Slack user. Requires human approval (HITL).

**Input:**
| Parameter | Type | Required |
|-----------|------|----------|
| `user_id` | string | Yes |
| `message` | string | Yes |

**Creates:** `Pending_Approval/SLACK_DM_{id}_{date}.md`

---

### `post_file`

Uploads a file to a Slack channel. Requires human approval (HITL).

**Input:**
| Parameter | Type | Required | Default |
|-----------|------|----------|---------|
| `channel` | string | No | `SLACK_TEAM_CHANNEL` |
| `file_path` | string | Yes | — |
| `title` | string | No | — |
| `comment` | string | No | — |

**Creates:** `Pending_Approval/SLACK_FILE_{id}_{date}.md`

---

### `get_mentions`

Fetches recent mentions of the bot in Slack (read-only, no approval needed).

**Input:**
| Parameter | Type | Required | Default |
|-----------|------|----------|---------|
| `count` | number | No | `10` |

**Returns:** Array of mention objects with `ts`, `channel`, `user`, `text`, `permalink`.

---

### `create_reminder`

Creates a Slack reminder for a user. Requires human approval (HITL).

**Input:**
| Parameter | Type | Required |
|-----------|------|----------|
| `text` | string | Yes |
| `time` | string | Yes (ISO 8601 or natural language) |
| `user_id` | string | No (defaults to bot) |

**Creates:** `Pending_Approval/SLACK_REMINDER_{id}_{date}.md`

---

## HITL Approval Workflow

Write tools create approval files, not live Slack API calls:

```
Pending_Approval/SLACK_MESSAGE_*.md   → Human approves → Approved/ → Message posted
Pending_Approval/SLACK_DM_*.md        → Human approves → Approved/ → DM sent
Pending_Approval/SLACK_FILE_*.md      → Human approves → Approved/ → File uploaded
Pending_Approval/SLACK_REMINDER_*.md  → Human approves → Approved/ → Reminder created
```

`get_mentions` is read-only and executes immediately without an approval file.

Resolved files (approved or rejected) move to `Done/` for audit trail.

---

## Cross-Domain Workflows

This server is used by `cross_domain_integration_demo.py`:

- **Workflow 1** — Personal urgent email → Slack channel notification to team
- **Workflow 2** — Business calendar meeting → Slack reminder for team lead
- **Workflow 3** — CEO briefing → Slack channel announcement + file upload

See `Skills/CROSS_DOMAIN_INTEGRATION_SKILL.md` for full workflow documentation.

---

## Slack Web API Endpoints Used

| Tool | Endpoint |
|------|----------|
| `send_channel_message` | `POST /api/chat.postMessage` |
| `send_dm` | `POST /api/conversations.open` + `chat.postMessage` |
| `post_file` | `POST /api/files.upload` |
| `get_mentions` | `GET /api/search.messages?query=<@{BOT_USER_ID}>` |
| `create_reminder` | `POST /api/reminders.add` |

Base URL: `https://slack.com`
Auth header: `Authorization: Bearer xoxb-{SLACK_BOT_TOKEN}`
