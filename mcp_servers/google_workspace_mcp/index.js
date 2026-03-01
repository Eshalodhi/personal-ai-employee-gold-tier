/**
 * Google Workspace MCP Server v1.0
 * ===================================
 * Tools: 6 — Google Calendar (2), Google Drive (3), Business Gmail (1)
 * Part of the AI Employee Vault Gold Tier — Cross-Domain Integration
 *
 * Domains covered:
 *   calendar_list_events       → List upcoming Calendar events
 *   calendar_create_event      → Create a Calendar event (HITL approval)
 *   drive_search_files         → Search files in Google Drive
 *   drive_upload_file          → Upload a vault file to Drive (HITL approval)
 *   drive_share_file           → Share a Drive file with users (HITL approval)
 *   gmail_business_search      → Search business Gmail account (read-only)
 *
 * All tools default to SIMULATION MODE — no real Google API calls until
 * credentials are configured. See README.md for OAuth setup.
 */

import { Server } from "@modelcontextprotocol/sdk/server/index.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import {
  CallToolRequestSchema,
  ListToolsRequestSchema,
} from "@modelcontextprotocol/sdk/types.js";
import fs from "fs";
import path from "path";
import { fileURLToPath } from "url";

// ============================================================
// CONFIGURATION
// ============================================================

const __filename = fileURLToPath(import.meta.url);
const __dirname  = path.dirname(__filename);

// Vault root — two levels up from mcp_servers/google_workspace_mcp/
const VAULT_PATH = path.resolve(__dirname, "..", "..");

// ── Simulation flags ──────────────────────────────────────────
// Set to false + configure credentials to go live per service.
const SIMULATE_CALENDAR = true;
const SIMULATE_DRIVE    = true;
const SIMULATE_GMAIL_BIZ = true;

// ── Google Calendar credentials (OAuth 2.0) ──────────────────
const GOOGLE_CLIENT_ID     = process.env.GOOGLE_CLIENT_ID     || "";
const GOOGLE_CLIENT_SECRET = process.env.GOOGLE_CLIENT_SECRET || "";
const GOOGLE_REFRESH_TOKEN = process.env.GOOGLE_REFRESH_TOKEN || "";
const BUSINESS_CALENDAR_ID = process.env.BUSINESS_CALENDAR_ID || "primary";

// ── Google Drive credentials (same OAuth token as Calendar) ───
const DRIVE_ROOT_FOLDER_ID = process.env.DRIVE_ROOT_FOLDER_ID || "";

// ── Business Gmail credentials (separate account from personal) ─
const GMAIL_BIZ_USER_ID    = process.env.GMAIL_BIZ_USER_ID    || "me";
const GMAIL_BIZ_REFRESH_TOKEN = process.env.GMAIL_BIZ_REFRESH_TOKEN || "";

// ── API base URLs ─────────────────────────────────────────────
const CALENDAR_API_BASE = "https://www.googleapis.com/calendar/v3";
const DRIVE_API_BASE    = "https://www.googleapis.com/drive/v3";
const GMAIL_API_BASE    = "https://gmail.googleapis.com/gmail/v1";

// ============================================================
// UTILITIES
// ============================================================

function log(msg) {
  process.stderr.write(`[google-workspace-mcp] ${msg}\n`);
}

function nowIso() {
  return new Date().toISOString();
}

function todayStr() {
  return new Date().toISOString().slice(0, 10);
}

function generateId() {
  return Math.floor(Math.random() * 0xFFFFFFFF).toString(16).toUpperCase().padStart(8, "0");
}

function successResult(data) {
  return {
    content: [{ type: "text", text: JSON.stringify(data, null, 2) }],
    isError: false,
  };
}

function errorResult(message) {
  return {
    content: [{ type: "text", text: `ERROR: ${message}` }],
    isError: true,
  };
}

function ensureDir(dirPath) {
  if (!fs.existsSync(dirPath)) fs.mkdirSync(dirPath, { recursive: true });
}

function expiresIso(hours = 24) {
  return new Date(Date.now() + hours * 3600 * 1000).toISOString();
}

// ============================================================
// APPROVAL FILE WRITERS
// ============================================================

function createCalendarApprovalFile(event) {
  ensureDir(path.join(VAULT_PATH, "Pending_Approval"));
  const id       = generateId();
  const filename = `CALENDAR_EVENT_${id}_${todayStr()}.md`;
  const filepath = path.join(VAULT_PATH, "Pending_Approval", filename);
  const expires  = expiresIso(24);

  const attendeeList = (event.attendees || []).map(a => `  - ${a}`).join("\n");

  const content = `---
type: calendar_event_approval
action: create_calendar_event
event_id: ${id}
calendar_id: ${event.calendar_id || BUSINESS_CALENDAR_ID}
created: ${nowIso()}
expires: ${expires}
status: pending
risk_level: low
requested_by: google_workspace_mcp
simulation_mode: ${SIMULATE_CALENDAR}
---

# Approval Request: Create Calendar Event

**Title:** ${event.title}
**Start:** ${event.start_time}
**End:**   ${event.end_time}
**Calendar:** ${event.calendar_id || BUSINESS_CALENDAR_ID}

## Event Details

${event.description || "(no description)"}

## Attendees
${attendeeList || "  (none)"}

## Details
- **Send notifications:** ${event.send_notifications ?? true}
- **Mode:** ${SIMULATE_CALENDAR ? "SIMULATION — no real Calendar API call" : "LIVE — Google Calendar API v3"}
- **Expires:** ${expires}

## To Approve → move to Approved/
## To Reject  → move to Rejected/

---
*Generated by google_workspace_mcp — AI Employee Vault Gold Tier*
`;

  fs.writeFileSync(filepath, content, "utf-8");
  log(`Calendar approval file created: ${filename}`);
  return { id, filename, filepath };
}

function createDriveUploadApprovalFile(upload) {
  ensureDir(path.join(VAULT_PATH, "Pending_Approval"));
  const id       = generateId();
  const filename = `DRIVE_UPLOAD_${id}_${todayStr()}.md`;
  const filepath = path.join(VAULT_PATH, "Pending_Approval", filename);
  const expires  = expiresIso(24);

  const content = `---
type: drive_upload_approval
action: drive_upload_file
upload_id: ${id}
created: ${nowIso()}
expires: ${expires}
status: pending
risk_level: medium
requested_by: google_workspace_mcp
simulation_mode: ${SIMULATE_DRIVE}
---

# Approval Request: Upload File to Google Drive

**Local file:** ${upload.file_path}
**Drive title:** ${upload.title || path.basename(upload.file_path)}
**Destination folder:** ${upload.folder_id || DRIVE_ROOT_FOLDER_ID || "(root)"}

## Description
${upload.description || "(none)"}

## Share After Upload
${upload.share_with ? `Share with: ${Array.isArray(upload.share_with) ? upload.share_with.join(", ") : upload.share_with}` : "No automatic sharing after upload."}

## Details
- **Mode:** ${SIMULATE_DRIVE ? "SIMULATION — no real Drive API call" : "LIVE — Google Drive API v3"}
- **Expires:** ${expires}

## To Approve → move to Approved/
## To Reject  → move to Rejected/

---
*Generated by google_workspace_mcp — AI Employee Vault Gold Tier*
`;

  fs.writeFileSync(filepath, content, "utf-8");
  log(`Drive upload approval file created: ${filename}`);
  return { id, filename, filepath };
}

function createDriveShareApprovalFile(share) {
  ensureDir(path.join(VAULT_PATH, "Pending_Approval"));
  const id       = generateId();
  const filename = `DRIVE_SHARE_${id}_${todayStr()}.md`;
  const filepath = path.join(VAULT_PATH, "Pending_Approval", filename);
  const expires  = expiresIso(24);

  const roleMap = { reader: "can view", writer: "can edit", commenter: "can comment" };
  const roleDesc = roleMap[share.role] || share.role;

  const content = `---
type: drive_share_approval
action: drive_share_file
share_id: ${id}
file_id: ${share.file_id}
created: ${nowIso()}
expires: ${expires}
status: pending
risk_level: medium
requested_by: google_workspace_mcp
simulation_mode: ${SIMULATE_DRIVE}
---

# Approval Request: Share Google Drive File

**File ID:** ${share.file_id}
**Recipients:** ${Array.isArray(share.email_addresses) ? share.email_addresses.join(", ") : share.email_addresses}
**Permission:** ${share.role} (${roleDesc})

## Message to Recipients
${share.message || "(no message)"}

## Details
- **Mode:** ${SIMULATE_DRIVE ? "SIMULATION — no real Drive API call" : "LIVE — Google Drive API v3"}
- **Expires:** ${expires}

## To Approve → move to Approved/
## To Reject  → move to Rejected/

---
*Generated by google_workspace_mcp — AI Employee Vault Gold Tier*
`;

  fs.writeFileSync(filepath, content, "utf-8");
  log(`Drive share approval file created: ${filename}`);
  return { id, filename, filepath };
}

// ============================================================
// TOOL: calendar_list_events
// ============================================================

async function calendarListEvents(args) {
  const {
    max_results = 10,
    time_min = new Date().toISOString(),
    time_max = new Date(Date.now() + 7 * 24 * 3600000).toISOString(),
    calendar_id = BUSINESS_CALENDAR_ID,
  } = args;

  log(`calendar_list_events: calendar=${calendar_id}, max=${max_results}, SIMULATE=${SIMULATE_CALENDAR}`);

  if (SIMULATE_CALENDAR) {
    // Return realistic mock events
    const mockEvents = [
      {
        id: "evt_001",
        title: "Weekly Team Standup",
        start: new Date(Date.now() + 86400000).toISOString(),
        end: new Date(Date.now() + 86400000 + 1800000).toISOString(),
        attendees: ["alice@company.com", "bob@company.com"],
        location: "Google Meet",
        description: "Weekly sync — review AI Employee progress, blockers, next steps.",
        status: "confirmed",
      },
      {
        id: "evt_002",
        title: "CEO Briefing Review",
        start: new Date(Date.now() + 2 * 86400000).toISOString(),
        end: new Date(Date.now() + 2 * 86400000 + 3600000).toISOString(),
        attendees: ["ceo@company.com", "cto@company.com"],
        location: "Conference Room B",
        description: "Review AI Employee weekly briefing report. Drive link shared in invite.",
        status: "confirmed",
      },
      {
        id: "evt_003",
        title: "AI Employee Demo",
        start: new Date(Date.now() + 3 * 86400000).toISOString(),
        end: new Date(Date.now() + 3 * 86400000 + 5400000).toISOString(),
        attendees: ["investors@vc.com", "team@company.com"],
        location: "Google Meet",
        description: "Live demonstration of Gold tier autonomous capabilities.",
        status: "confirmed",
      },
    ].slice(0, max_results);

    return successResult({
      simulation: true,
      calendar_id,
      time_range: { from: time_min, to: time_max },
      events_found: mockEvents.length,
      events: mockEvents,
      note: "SIMULATION MODE — set SIMULATE_CALENDAR=false + configure Google OAuth to use real Calendar API",
    });
  }

  // PRODUCTION: Real Google Calendar API call
  // Requires: googleapis npm package + OAuth 2.0 token
  return errorResult("LIVE mode not yet configured. Set Google OAuth credentials and set SIMULATE_CALENDAR=false.");
}

// ============================================================
// TOOL: calendar_create_event
// ============================================================

async function calendarCreateEvent(args) {
  const {
    title,
    description = "",
    start_time,
    end_time,
    attendees = [],
    calendar_id = BUSINESS_CALENDAR_ID,
    send_notifications = true,
  } = args;

  if (!title)      return errorResult("title is required");
  if (!start_time) return errorResult("start_time is required (ISO 8601)");
  if (!end_time)   return errorResult("end_time is required (ISO 8601)");

  log(`calendar_create_event: "${title}" ${start_time}→${end_time}, SIMULATE=${SIMULATE_CALENDAR}`);

  const eventData = { title, description, start_time, end_time, attendees, calendar_id, send_notifications };

  if (SIMULATE_CALENDAR) {
    const { id, filename, filepath } = createCalendarApprovalFile(eventData);
    return successResult({
      simulation: true,
      status: "pending_approval",
      event_id: id,
      event: {
        title,
        start: start_time,
        end: end_time,
        attendees,
        calendar_id,
      },
      approval_file: filename,
      approval_path: filepath,
      message: `Calendar event approval created. Move ${filename} to Approved/ to confirm creation.`,
      hitl_required: true,
    });
  }

  // PRODUCTION: POST /calendar/v3/calendars/{calendarId}/events
  return errorResult("LIVE mode not yet configured. Set Google OAuth credentials.");
}

// ============================================================
// TOOL: drive_search_files
// ============================================================

async function driveSearchFiles(args) {
  const {
    query,
    max_results = 10,
    folder_id = "",
  } = args;

  if (!query) return errorResult("query is required (e.g. 'CEO Briefing' or 'name contains briefing')");

  log(`drive_search_files: query="${query}", max=${max_results}, SIMULATE=${SIMULATE_DRIVE}`);

  if (SIMULATE_DRIVE) {
    const queryLower = query.toLowerCase();
    const mockFiles = [
      {
        id: "1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgVE2upms",
        name: "CEO_Briefing_2026-02-23.md",
        mimeType: "text/markdown",
        modifiedTime: "2026-02-23T10:45:00Z",
        size: 4973,
        webViewLink: "https://drive.google.com/file/d/1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgVE2upms",
        parents: ["DRIVE_ROOT_FOLDER"],
      },
      {
        id: "1cRb5npkEqQ2D2fJVLmBzKvMpLhJ3gL4mRSTl0wlJvXI",
        name: "AI_Employee_Architecture.pdf",
        mimeType: "application/pdf",
        modifiedTime: "2026-02-20T09:30:00Z",
        size: 248192,
        webViewLink: "https://drive.google.com/file/d/1cRb5npkEqQ2D2fJVLmBzKvMpLhJ3gL4mRSTl0wlJvXI",
        parents: ["DRIVE_ROOT_FOLDER"],
      },
      {
        id: "1dZpK9fVpQrXmNz2JDo8EyApHkNLpQw3tU5Vl6gKyOWA",
        name: "Weekly_Status_Report.docx",
        mimeType: "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        modifiedTime: "2026-02-24T16:00:00Z",
        size: 35840,
        webViewLink: "https://drive.google.com/file/d/1dZpK9fVpQrXmNz2JDo8EyApHkNLpQw3tU5Vl6gKyOWA",
        parents: ["DRIVE_ROOT_FOLDER"],
      },
    ]
    .filter(f => f.name.toLowerCase().includes(queryLower) || queryLower.includes("all"))
    .slice(0, max_results);

    return successResult({
      simulation: true,
      query,
      folder_id: folder_id || "(root)",
      files_found: mockFiles.length,
      files: mockFiles,
      note: "SIMULATION MODE — set SIMULATE_DRIVE=false + configure Google OAuth to use real Drive API",
    });
  }

  // PRODUCTION: GET /drive/v3/files?q={query}&pageSize={max}
  return errorResult("LIVE mode not yet configured. Set Google OAuth credentials.");
}

// ============================================================
// TOOL: drive_upload_file
// ============================================================

async function driveUploadFile(args) {
  const {
    file_path,
    folder_id = DRIVE_ROOT_FOLDER_ID,
    title = "",
    description = "",
    share_with = [],
  } = args;

  if (!file_path) return errorResult("file_path is required (relative to vault root)");

  const absolutePath = path.join(VAULT_PATH, file_path);
  if (!SIMULATE_DRIVE && !fs.existsSync(absolutePath)) {
    return errorResult(`File not found: ${absolutePath}`);
  }

  const resolvedTitle = title || path.basename(file_path);
  log(`drive_upload_file: "${file_path}" → Drive as "${resolvedTitle}", SIMULATE=${SIMULATE_DRIVE}`);

  const uploadData = { file_path, folder_id, title: resolvedTitle, description, share_with };

  if (SIMULATE_DRIVE) {
    const { id, filename, filepath } = createDriveUploadApprovalFile(uploadData);
    return successResult({
      simulation: true,
      status: "pending_approval",
      upload_id: id,
      upload: {
        local_file: file_path,
        drive_title: resolvedTitle,
        folder_id: folder_id || "(root)",
        description,
        share_with,
      },
      approval_file: filename,
      approval_path: filepath,
      message: `Drive upload approval created. Move ${filename} to Approved/ to confirm upload.`,
      hitl_required: true,
    });
  }

  // PRODUCTION: POST https://www.googleapis.com/upload/drive/v3/files (multipart)
  return errorResult("LIVE mode not yet configured. Set Google OAuth credentials.");
}

// ============================================================
// TOOL: drive_share_file
// ============================================================

async function driveShareFile(args) {
  const {
    file_id,
    email_addresses,
    role = "reader",
    message = "",
  } = args;

  if (!file_id)         return errorResult("file_id is required");
  if (!email_addresses) return errorResult("email_addresses is required (string or array)");

  const emails = Array.isArray(email_addresses) ? email_addresses : [email_addresses];
  const validRoles = ["reader", "writer", "commenter"];
  if (!validRoles.includes(role)) return errorResult(`role must be one of: ${validRoles.join(", ")}`);

  log(`drive_share_file: file=${file_id}, recipients=${emails.join(",")}, role=${role}, SIMULATE=${SIMULATE_DRIVE}`);

  const shareData = { file_id, email_addresses: emails, role, message };

  if (SIMULATE_DRIVE) {
    const { id, filename, filepath } = createDriveShareApprovalFile(shareData);
    return successResult({
      simulation: true,
      status: "pending_approval",
      share_id: id,
      share: {
        file_id,
        recipients: emails,
        role,
        message,
      },
      approval_file: filename,
      approval_path: filepath,
      message: `Drive share approval created. Move ${filename} to Approved/ to confirm sharing.`,
      hitl_required: true,
    });
  }

  // PRODUCTION: POST /drive/v3/files/{fileId}/permissions (one per recipient)
  return errorResult("LIVE mode not yet configured. Set Google OAuth credentials.");
}

// ============================================================
// TOOL: gmail_business_search
// ============================================================

async function gmailBusinessSearch(args) {
  const {
    query,
    max_results = 10,
    label_ids = ["INBOX"],
  } = args;

  if (!query) return errorResult("query is required (Gmail search syntax, e.g. 'from:ceo@company.com is:unread')");

  log(`gmail_business_search: query="${query}", max=${max_results}, SIMULATE=${SIMULATE_GMAIL_BIZ}`);

  if (SIMULATE_GMAIL_BIZ) {
    const mockEmails = [
      {
        id: "msg_biz_001",
        threadId: "thread_001",
        subject: "Q1 Board Report — Action Required",
        from: "ceo@company.com",
        to: "ai-employee@company.com",
        date: new Date(Date.now() - 3600000).toISOString(),
        snippet: "Please prepare the Q1 board report summary and distribute to stakeholders by Friday...",
        labels: ["INBOX", "IMPORTANT"],
        priority: "urgent",
      },
      {
        id: "msg_biz_002",
        threadId: "thread_002",
        subject: "Investor Update — February 2026",
        from: "investors@vc.com",
        to: "team@company.com",
        date: new Date(Date.now() - 7200000).toISOString(),
        snippet: "Following the demo last week, we'd like to schedule a follow-up call to discuss...",
        labels: ["INBOX"],
        priority: "normal",
      },
      {
        id: "msg_biz_003",
        threadId: "thread_003",
        subject: "Team Lunch — Thursday",
        from: "office@company.com",
        to: "team@company.com",
        date: new Date(Date.now() - 86400000).toISOString(),
        snippet: "Just a reminder that team lunch is Thursday at 12:30 PM at The Harbour. Please RSVP...",
        labels: ["INBOX"],
        priority: "normal",
      },
    ]
    .filter((_, i) => i < max_results);

    return successResult({
      simulation: true,
      account: GMAIL_BIZ_USER_ID !== "me" ? GMAIL_BIZ_USER_ID : "business_account@company.com (simulated)",
      query,
      labels: label_ids,
      emails_found: mockEmails.length,
      emails: mockEmails,
      note: "SIMULATION MODE — set SIMULATE_GMAIL_BIZ=false + configure GMAIL_BIZ_REFRESH_TOKEN to search real business Gmail",
    });
  }

  // PRODUCTION: GET /gmail/v1/users/{userId}/messages?q={query}&labelIds={labels}
  return errorResult("LIVE mode not yet configured. Set business Gmail OAuth credentials.");
}

// ============================================================
// MCP SERVER SETUP
// ============================================================

const server = new Server(
  { name: "google-workspace-mcp", version: "1.0.0" },
  { capabilities: { tools: {} } }
);

// ── Tool definitions ──────────────────────────────────────────

server.setRequestHandler(ListToolsRequestSchema, async () => ({
  tools: [
    {
      name: "calendar_list_events",
      description: "List upcoming events from the business Google Calendar. Returns event titles, times, attendees, and locations.",
      inputSchema: {
        type: "object",
        properties: {
          max_results:  { type: "number",  description: "Maximum events to return (default: 10)" },
          time_min:     { type: "string",  description: "Start of time range in ISO 8601 (default: now)" },
          time_max:     { type: "string",  description: "End of time range in ISO 8601 (default: 7 days from now)" },
          calendar_id:  { type: "string",  description: "Calendar ID to query (default: primary business calendar)" },
        },
      },
    },
    {
      name: "calendar_create_event",
      description: "Create a new event on the business Google Calendar. Requires HITL approval before the API call is made.",
      inputSchema: {
        type: "object",
        properties: {
          title:              { type: "string",  description: "Event title" },
          description:        { type: "string",  description: "Event description / agenda" },
          start_time:         { type: "string",  description: "Start time in ISO 8601 (e.g. 2026-03-01T09:00:00+05:00)" },
          end_time:           { type: "string",  description: "End time in ISO 8601" },
          attendees:          { type: "array",   items: { type: "string" }, description: "List of attendee email addresses" },
          calendar_id:        { type: "string",  description: "Calendar ID (default: primary)" },
          send_notifications: { type: "boolean", description: "Send email invites to attendees (default: true)" },
        },
        required: ["title", "start_time", "end_time"],
      },
    },
    {
      name: "drive_search_files",
      description: "Search for files in Google Drive. Supports Drive query syntax (e.g. 'name contains briefing', 'mimeType=application/pdf').",
      inputSchema: {
        type: "object",
        properties: {
          query:       { type: "string",  description: "Drive search query (supports Drive query syntax)" },
          max_results: { type: "number",  description: "Maximum files to return (default: 10)" },
          folder_id:   { type: "string",  description: "Limit search to a specific folder ID (optional)" },
        },
        required: ["query"],
      },
    },
    {
      name: "drive_upload_file",
      description: "Upload a local vault file to Google Drive. Requires HITL approval. Optionally share with users after upload.",
      inputSchema: {
        type: "object",
        properties: {
          file_path:   { type: "string",  description: "Path to the file relative to vault root (e.g. Reports/CEO_Briefing_2026-02-23.md)" },
          folder_id:   { type: "string",  description: "Google Drive folder ID to upload into (optional — defaults to root)" },
          title:       { type: "string",  description: "Title for the file in Drive (defaults to filename)" },
          description: { type: "string",  description: "File description in Drive (optional)" },
          share_with:  { type: "array",   items: { type: "string" }, description: "Email addresses to share the file with after upload (optional)" },
        },
        required: ["file_path"],
      },
    },
    {
      name: "drive_share_file",
      description: "Share a Google Drive file with one or more users. Requires HITL approval.",
      inputSchema: {
        type: "object",
        properties: {
          file_id:         { type: "string", description: "Google Drive file ID" },
          email_addresses: {
            oneOf: [
              { type: "string" },
              { type: "array", items: { type: "string" } },
            ],
            description: "Email address or list of addresses to share with",
          },
          role:    { type: "string", enum: ["reader", "writer", "commenter"], description: "Permission level (default: reader)" },
          message: { type: "string", description: "Optional message to include in the share notification" },
        },
        required: ["file_id", "email_addresses"],
      },
    },
    {
      name: "gmail_business_search",
      description: "Search the business Gmail account (separate from personal Gmail). Supports standard Gmail search syntax. Read-only — no HITL required.",
      inputSchema: {
        type: "object",
        properties: {
          query:      { type: "string", description: "Gmail search query (e.g. 'from:ceo@company.com is:unread subject:urgent')" },
          max_results:{ type: "number", description: "Maximum emails to return (default: 10)" },
          label_ids:  { type: "array", items: { type: "string" }, description: "Label filters (default: ['INBOX'])" },
        },
        required: ["query"],
      },
    },
  ],
}));

// ── Tool dispatcher ───────────────────────────────────────────

server.setRequestHandler(CallToolRequestSchema, async (request) => {
  const { name, arguments: args = {} } = request.params;
  log(`Tool called: ${name}`);
  try {
    switch (name) {
      case "calendar_list_events":  return await calendarListEvents(args);
      case "calendar_create_event": return await calendarCreateEvent(args);
      case "drive_search_files":    return await driveSearchFiles(args);
      case "drive_upload_file":     return await driveUploadFile(args);
      case "drive_share_file":      return await driveShareFile(args);
      case "gmail_business_search": return await gmailBusinessSearch(args);
      default: return errorResult(`Unknown tool: ${name}`);
    }
  } catch (err) {
    log(`Error in tool ${name}: ${err.message}`);
    return errorResult(`Internal error: ${err.message}`);
  }
});

// ── Start ─────────────────────────────────────────────────────

const transport = new StdioServerTransport();
await server.connect(transport);

log("Google Workspace MCP Server v1.0.0 started");
log(`Vault: ${VAULT_PATH}`);
log(`Mode: Calendar=${SIMULATE_CALENDAR?"SIM":"LIVE"} Drive=${SIMULATE_DRIVE?"SIM":"LIVE"} Gmail-Biz=${SIMULATE_GMAIL_BIZ?"SIM":"LIVE"}`);
log("Tools: calendar_list_events, calendar_create_event, drive_search_files, drive_upload_file, drive_share_file, gmail_business_search");
