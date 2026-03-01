# Google Workspace MCP Server

MCP server providing Claude Code with access to Google Calendar, Google Drive, and Business Gmail.

**Status:** SIMULATION MODE (default) — flip flags + set credentials to go live
**Tools:** 6
**Version:** 1.0.0

---

## Tools

| Tool | Domain | Requires Approval |
|------|--------|-------------------|
| `calendar_list_events` | Google Calendar | No (read-only) |
| `calendar_create_event` | Google Calendar | Yes |
| `drive_search_files` | Google Drive | No (read-only) |
| `drive_upload_file` | Google Drive | Yes |
| `drive_share_file` | Google Drive | Yes |
| `gmail_business_search` | Business Gmail | No (read-only) |

---

## Setup

### 1. Create a Google Cloud Project

1. Go to [console.cloud.google.com](https://console.cloud.google.com)
2. Create a new project (e.g. `ai-employee-workspace`)
3. Enable these APIs:
   - Google Calendar API
   - Google Drive API
   - Gmail API

### 2. Create OAuth 2.0 Credentials

1. Go to **APIs & Services → Credentials → Create Credentials → OAuth client ID**
2. Application type: **Desktop app**
3. Download the JSON — note `client_id` and `client_secret`

### 3. Get Refresh Tokens

#### Calendar + Drive (shared token)

```bash
# Install google-auth-oauthlib
pip install google-auth-oauthlib

# Run OAuth flow (opens browser)
python - <<'EOF'
from google_auth_oauthlib.flow import InstalledAppFlow
SCOPES = [
    "https://www.googleapis.com/auth/calendar",
    "https://www.googleapis.com/auth/drive",
]
flow = InstalledAppFlow.from_client_secrets_file("credentials.json", SCOPES)
creds = flow.run_local_server(port=0)
print("REFRESH TOKEN:", creds.refresh_token)
EOF
```

#### Business Gmail (separate token — different account)

```bash
python - <<'EOF'
from google_auth_oauthlib.flow import InstalledAppFlow
SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]
flow = InstalledAppFlow.from_client_secrets_file("credentials.json", SCOPES)
creds = flow.run_local_server(port=0)
print("BIZ GMAIL REFRESH TOKEN:", creds.refresh_token)
EOF
```

### 4. Set Environment Variables

```bash
# Windows
set GOOGLE_CLIENT_ID=your-client-id.apps.googleusercontent.com
set GOOGLE_CLIENT_SECRET=your-client-secret
set GOOGLE_REFRESH_TOKEN=your-refresh-token-for-calendar-drive
set BUSINESS_CALENDAR_ID=primary
set DRIVE_ROOT_FOLDER_ID=optional-folder-id-to-scope-uploads
set GMAIL_BIZ_USER_ID=business@company.com
set GMAIL_BIZ_REFRESH_TOKEN=your-refresh-token-for-biz-gmail

# Linux/macOS
export GOOGLE_CLIENT_ID=...
```

### 5. Enable Live Mode

Edit `mcp_servers/google_workspace_mcp/index.js`:

```javascript
// Change these from true to false:
const SIMULATE_CALENDAR  = false;
const SIMULATE_DRIVE     = false;
const SIMULATE_GMAIL_BIZ = false;
```

### 6. Install & Test

```bash
cd mcp_servers/google_workspace_mcp
npm install
node index.js
# Should print: Google Workspace MCP Server running on stdio
```

---

## API Reference

### `calendar_list_events`

Lists upcoming events from Google Calendar.

**Input:**
| Parameter | Type | Required | Default |
|-----------|------|----------|---------|
| `calendar_id` | string | No | `"primary"` |
| `max_results` | number | No | `10` |
| `time_min` | string (ISO 8601) | No | now |
| `time_max` | string (ISO 8601) | No | — |

**Returns:** Array of event objects with `id`, `summary`, `start`, `end`, `attendees`, `description`.

---

### `calendar_create_event`

Creates a calendar event. Requires human approval (HITL).

**Input:**
| Parameter | Type | Required |
|-----------|------|----------|
| `summary` | string | Yes |
| `start_datetime` | string (ISO 8601) | Yes |
| `end_datetime` | string (ISO 8601) | Yes |
| `description` | string | No |
| `attendees` | string[] | No |
| `calendar_id` | string | No |

**Creates:** `Pending_Approval/CALENDAR_EVENT_{id}_{date}.md`

---

### `drive_search_files`

Searches files in Google Drive.

**Input:**
| Parameter | Type | Required | Default |
|-----------|------|----------|---------|
| `query` | string | Yes | — |
| `max_results` | number | No | `10` |
| `folder_id` | string | No | — |

**Returns:** Array of file objects with `id`, `name`, `mimeType`, `modifiedTime`, `webViewLink`.

---

### `drive_upload_file`

Uploads a local file to Google Drive. Requires human approval (HITL).

**Input:**
| Parameter | Type | Required |
|-----------|------|----------|
| `file_path` | string | Yes |
| `file_name` | string | Yes |
| `mime_type` | string | No |
| `folder_id` | string | No |
| `description` | string | No |

**Creates:** `Pending_Approval/DRIVE_UPLOAD_{id}_{date}.md`

---

### `drive_share_file`

Shares a Drive file with a user or domain. Requires human approval (HITL).

**Input:**
| Parameter | Type | Required |
|-----------|------|----------|
| `file_id` | string | Yes |
| `email` | string | Yes |
| `role` | string | No (`"reader"`) |
| `type` | string | No (`"user"`) |

**Creates:** `Pending_Approval/DRIVE_SHARE_{id}_{date}.md`

---

### `gmail_business_search`

Searches business Gmail inbox (read-only).

**Input:**
| Parameter | Type | Required | Default |
|-----------|------|----------|---------|
| `query` | string | Yes | — |
| `max_results` | number | No | `10` |
| `user_id` | string | No | `"me"` |

**Returns:** Array of message objects with `id`, `subject`, `from`, `date`, `snippet`.

---

## HITL Approval Workflow

Write tools create approval files, not live API calls:

```
Pending_Approval/CALENDAR_EVENT_*.md   → Human approves → Approved/ → Live calendar event created
Pending_Approval/DRIVE_UPLOAD_*.md     → Human approves → Approved/ → File uploaded to Drive
Pending_Approval/DRIVE_SHARE_*.md      → Human approves → Approved/ → File shared with user
```

Resolved files (approved or rejected) move to `Done/` for audit trail.

---

## Cross-Domain Workflows

This server is used by `cross_domain_integration_demo.py`:

- **Workflow 1** — Personal email → Calendar event + Drive upload
- **Workflow 2** — Business calendar → Personal reminder
- **Workflow 3** — CEO briefing → Drive upload + Calendar event

See `Skills/CROSS_DOMAIN_INTEGRATION_SKILL.md` for full workflow documentation.

---

## Required OAuth Scopes

| Scope | Purpose |
|-------|---------|
| `https://www.googleapis.com/auth/calendar` | Read + write calendar events |
| `https://www.googleapis.com/auth/drive` | Read + write Drive files |
| `https://www.googleapis.com/auth/gmail.readonly` | Read business Gmail |
