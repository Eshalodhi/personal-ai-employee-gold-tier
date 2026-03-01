/**
 * AI Employee Vault - LinkedIn MCP Server
 * =========================================
 * Gold Tier MCP server for LinkedIn content management.
 *
 * ⚠️  SIMULATION MODE (default: true)
 * LinkedIn's Marketing Developer Platform requires company verification
 * before granting w_member_social posting access. Until approved, this
 * server runs in simulation mode:
 *   - Creates HITL approval requests in Pending_Approval/
 *   - Logs exactly what WOULD be posted to LinkedIn
 *   - Saves scheduled posts as plan files
 *   - All real API calls are fully implemented but wrapped in
 *     /* PRODUCTION_ONLY ... * / blocks — flip SIMULATION_MODE = false
 *     and supply a valid ACCESS_TOKEN to go live.
 *
 * Tools provided:
 *   1. create_linkedin_post      — Draft & approve a LinkedIn post
 *   2. schedule_linkedin_post    — Queue a post for future publishing
 *   3. generate_business_content — AI-template content generation
 *
 * Usage:
 *   node index.js
 *
 * Launched automatically by Claude Code via .claude/mcp_config.json.
 */

import { Server } from "@modelcontextprotocol/sdk/server/index.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import {
  CallToolRequestSchema,
  ListToolsRequestSchema,
} from "@modelcontextprotocol/sdk/types.js";
import fs from "fs";
import fsp from "fs/promises";
import path from "path";
import { fileURLToPath } from "url";

// ============================================================
// CONFIGURATION
// ============================================================

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

/** Vault root — two levels up from mcp_servers/linkedin_mcp/ */
const VAULT_PATH = path.resolve(__dirname, "..", "..");

/**
 * SIMULATION_MODE = true  →  No real API calls. Creates approval files,
 *                             logs actions, returns simulated IDs.
 * SIMULATION_MODE = false →  Live LinkedIn API calls. Requires ACCESS_TOKEN.
 */
const SIMULATION_MODE = true;

/**
 * LinkedIn OAuth Access Token.
 * In production: obtain via OAuth 2.0 flow (see README.md).
 * In simulation: unused.
 */
const LINKEDIN_ACCESS_TOKEN = process.env.LINKEDIN_ACCESS_TOKEN || "";

/**
 * LinkedIn Member URN — your profile ID.
 * Format: "urn:li:person:{id}"  (find via GET /v2/me)
 * In simulation: uses placeholder.
 */
const LINKEDIN_PERSON_URN =
  process.env.LINKEDIN_PERSON_URN || "urn:li:person:DEMO_ID";

/** LinkedIn API base URL */
const LINKEDIN_API_BASE = "https://api.linkedin.com";

/** Path to content templates */
const TEMPLATES_PATH = path.join(__dirname, "linkedin_templates.json");

const LOG_PREFIX = "[linkedin-mcp]";

// ============================================================
// UTILITIES
// ============================================================

/**
 * Structured JSON log line → stderr (not sent to MCP client).
 */
function log(level, message, meta = {}) {
  const entry = { ts: new Date().toISOString(), level, msg: message, ...meta };
  process.stderr.write(`${LOG_PREFIX} ${JSON.stringify(entry)}\n`);
}

/** Generate a short unique post ID (8 hex chars). */
function generatePostId() {
  return Math.random().toString(16).slice(2, 10).toUpperCase();
}

/** Current date string for filenames. */
function dateStamp() {
  return new Date().toISOString().slice(0, 10);
}

/** ISO timestamp for file content. */
function isoNow() {
  return new Date().toISOString();
}

/** Load and parse linkedin_templates.json. */
function loadTemplates() {
  try {
    return JSON.parse(fs.readFileSync(TEMPLATES_PATH, "utf8"));
  } catch (err) {
    log("WARN", "Could not load templates", { error: err.message });
    return { post_types: {}, hashtag_suggestions: {}, best_practices: [] };
  }
}

/** Build the final post text: content + formatted hashtag block. */
function buildPostText(content, hashtags = []) {
  const trimmed = content.trim();
  if (hashtags.length === 0) return trimmed;
  const tagBlock = hashtags
    .map((h) => (h.startsWith("#") ? h : `#${h}`))
    .join(" ");
  return `${trimmed}\n\n${tagBlock}`;
}

/** Standard MCP success response. */
function successResult(data) {
  return {
    content: [
      { type: "text", text: JSON.stringify({ status: "success", ...data }, null, 2) },
    ],
  };
}

/** Standard MCP error response. */
function errorResult(message, hint) {
  const body = { status: "error", error: message };
  if (hint) body.hint = hint;
  return {
    content: [{ type: "text", text: JSON.stringify(body, null, 2) }],
    isError: true,
  };
}

// ============================================================
// APPROVAL / PLAN FILE WRITERS
// ============================================================

/**
 * Write a HITL approval request to Pending_Approval/.
 *
 * @param {object} post
 * @param {string} post.id
 * @param {string} post.content
 * @param {string[]} post.hashtags
 * @param {string} post.visibility
 * @param {string} post.post_text   fully formatted text
 * @param {string} post.created_at
 * @returns {Promise<string>} path to approval file
 */
async function createApprovalFile(post) {
  const dir = path.join(VAULT_PATH, "Pending_Approval");
  await fsp.mkdir(dir, { recursive: true });

  const filename = `LINKEDIN_POST_${post.id}_${dateStamp()}.md`;
  const filePath = path.join(dir, filename);

  const charCount = post.post_text.length;
  const templates = loadTemplates();
  const limits = templates.post_limits || {};
  const maxChars = limits.max_characters || 3000;
  const charWarning =
    charCount > maxChars
      ? `\n> ⚠️ WARNING: Post exceeds LinkedIn's ${maxChars}-character limit (${charCount} chars).`
      : "";

  const content = `---
type: LINKEDIN_POST_APPROVAL
post_id: ${post.id}
created_at: ${post.created_at}
status: PENDING_APPROVAL
simulation_mode: ${SIMULATION_MODE}
---

# LinkedIn Post Approval Request

**Post ID:** \`${post.id}\`
**Created:** ${post.created_at}
**Visibility:** ${post.visibility}
**Character Count:** ${charCount} / ${maxChars}
${charWarning}

## Post Preview

> *Exactly as it will appear on LinkedIn:*

---

${post.post_text}

---

## Metadata

| Field | Value |
|---|---|
| Hashtags | ${post.hashtags.length > 0 ? post.hashtags.join(", ") : "None"} |
| Visibility | ${post.visibility} |
| Simulation Mode | ${SIMULATION_MODE} |
| Scheduled | Immediate on approval |

## How to Approve

1. Review the post content above
2. If approved: move this file to \`Approved/\`
3. If rejected: move this file to \`Rejected/\`
4. Claude will detect the move and act accordingly

## What Happens on Approval

${
  SIMULATION_MODE
    ? `**SIMULATION MODE** — No real LinkedIn post will be created.\nClaude will log the simulated action and move this file to \`Done/\`.`
    : `**LIVE MODE** — Claude will call the LinkedIn Posts API and publish the post.\nThe real post URL will be logged to \`Done/\`.`
}

---
*Generated by LinkedIn MCP Server v1.0.0 (${SIMULATION_MODE ? "SIMULATION" : "LIVE"} mode)*
`;

  await fsp.writeFile(filePath, content, "utf8");
  log("INFO", "approval file created", { filePath, post_id: post.id });
  return filePath;
}

/**
 * Write a scheduled post plan to Plans/.
 *
 * @param {object} post
 * @returns {Promise<string>} path to plan file
 */
async function createScheduledPlanFile(post) {
  const dir = path.join(VAULT_PATH, "Plans");
  await fsp.mkdir(dir, { recursive: true });

  const filename = `LINKEDIN_SCHEDULED_${post.id}_${dateStamp()}.md`;
  const filePath = path.join(dir, filename);

  const content = `---
type: LINKEDIN_SCHEDULED_POST
post_id: ${post.id}
created_at: ${post.created_at}
scheduled_for: ${post.scheduled_time}
status: SCHEDULED
simulation_mode: ${SIMULATION_MODE}
---

# Scheduled LinkedIn Post

**Post ID:** \`${post.id}\`
**Created:** ${post.created_at}
**Scheduled For:** ${post.scheduled_time}
**Visibility:** ${post.visibility}

## Post Content

---

${post.post_text}

---

## Schedule Details

| Field | Value |
|---|---|
| Post ID | \`${post.id}\` |
| Scheduled Time | ${post.scheduled_time} |
| Hashtags | ${post.hashtags.join(", ") || "None"} |
| Visibility | ${post.visibility} |
| Mode | ${SIMULATION_MODE ? "SIMULATION" : "LIVE"} |

## Execution Plan

${
  SIMULATION_MODE
    ? `1. At scheduled time, Claude reviews this plan file
2. **SIMULATION**: Logs simulated post action (no real API call)
3. Moves plan to \`Done/\` with simulation notes`
    : `1. At scheduled time, Claude reviews this plan file
2. Calls LinkedIn Posts API: \`POST ${LINKEDIN_API_BASE}/rest/posts\`
3. Logs real post URL and moves plan to \`Done/\``
}

## LinkedIn API Payload (for reference)

\`\`\`json
${JSON.stringify(
  {
    author: LINKEDIN_PERSON_URN,
    lifecycleState: "PUBLISHED",
    specificContent: {
      "com.linkedin.ugc.ShareContent": {
        shareCommentary: { text: post.post_text },
        shareMediaCategory: "NONE",
      },
    },
    visibility: {
      "com.linkedin.ugc.MemberNetworkVisibility": post.visibility,
    },
  },
  null,
  2
)}
\`\`\`

---
*Generated by LinkedIn MCP Server v1.0.0 (${SIMULATION_MODE ? "SIMULATION" : "LIVE"} mode)*
`;

  await fsp.writeFile(filePath, content, "utf8");
  log("INFO", "scheduled plan file created", { filePath, post_id: post.id });
  return filePath;
}

// ============================================================
// REAL LINKEDIN API (PRODUCTION — commented out)
// ============================================================

/*
 * PRODUCTION_ONLY: Uncomment when SIMULATION_MODE = false and you have
 * a valid ACCESS_TOKEN from the OAuth 2.0 flow (see README.md).
 *
 * LinkedIn OAuth 2.0 Flow (Authorization Code):
 * -----------------------------------------------
 * Step 1 — Direct user to:
 *   https://www.linkedin.com/oauth/v2/authorization
 *     ?response_type=code
 *     &client_id={CLIENT_ID}
 *     &redirect_uri={REDIRECT_URI}
 *     &scope=w_member_social%20r_liteprofile%20r_emailaddress
 *     &state={RANDOM_STATE}
 *
 * Step 2 — Exchange code for token:
 *   POST https://www.linkedin.com/oauth/v2/accessToken
 *   Body (application/x-www-form-urlencoded):
 *     grant_type=authorization_code
 *     &code={CODE}
 *     &redirect_uri={REDIRECT_URI}
 *     &client_id={CLIENT_ID}
 *     &client_secret={CLIENT_SECRET}
 *   Response: { access_token, expires_in, refresh_token, ... }
 *
 * Step 3 — Get your person URN:
 *   GET https://api.linkedin.com/v2/me
 *   Header: Authorization: Bearer {ACCESS_TOKEN}
 *   Response includes: id → build URN as "urn:li:person:{id}"
 */

/*
async function publishToLinkedIn(postText, visibility) {
  if (!LINKEDIN_ACCESS_TOKEN) {
    throw new Error("LINKEDIN_ACCESS_TOKEN not set. See README for OAuth setup.");
  }

  // Build UGC Post payload (LinkedIn v2 API)
  const payload = {
    author: LINKEDIN_PERSON_URN,
    lifecycleState: "PUBLISHED",
    specificContent: {
      "com.linkedin.ugc.ShareContent": {
        shareCommentary: { text: postText },
        shareMediaCategory: "NONE",
      },
    },
    visibility: {
      "com.linkedin.ugc.MemberNetworkVisibility": visibility,
    },
  };

  const response = await fetch(`${LINKEDIN_API_BASE}/v2/ugcPosts`, {
    method: "POST",
    headers: {
      "Authorization": `Bearer ${LINKEDIN_ACCESS_TOKEN}`,
      "Content-Type": "application/json",
      "X-Restli-Protocol-Version": "2.0.0",
      "LinkedIn-Version": "202304",
    },
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    const errorBody = await response.text();
    throw new Error(`LinkedIn API error ${response.status}: ${errorBody}`);
  }

  // LinkedIn returns the post URN in the X-RestLi-Id header
  const postUrn = response.headers.get("X-RestLi-Id") || response.headers.get("x-restli-id");
  const data = await response.json().catch(() => ({}));

  return {
    post_urn: postUrn,
    post_url: postUrn
      ? `https://www.linkedin.com/feed/update/${encodeURIComponent(postUrn)}/`
      : null,
    raw: data,
  };
}
*/

/*
async function getLinkedInProfile() {
  // GET /v2/me — retrieve your member profile
  const response = await fetch(`${LINKEDIN_API_BASE}/v2/me`, {
    headers: {
      "Authorization": `Bearer ${LINKEDIN_ACCESS_TOKEN}`,
      "X-Restli-Protocol-Version": "2.0.0",
    },
  });
  if (!response.ok) throw new Error(`Profile fetch failed: ${response.status}`);
  return response.json();
}
*/

// ============================================================
// TOOL IMPLEMENTATIONS
// ============================================================

// ----------------------------------------------------------
// 1. create_linkedin_post
// ----------------------------------------------------------

/**
 * Create a LinkedIn post (or approval request in simulation mode).
 *
 * @param {object} args
 * @param {string} args.content       Post body text
 * @param {string[]} [args.hashtags]  Hashtags (with or without #)
 * @param {string} [args.visibility]  "PUBLIC" | "CONNECTIONS" | "LOGGED_IN"
 * @returns {Promise<object>}
 */
async function createLinkedInPost(args) {
  const {
    content,
    hashtags = [],
    visibility = "PUBLIC",
  } = args;

  // Validate
  if (!content || content.trim().length === 0) {
    return errorResult("'content' is required and cannot be empty.");
  }

  const validVisibility = ["PUBLIC", "CONNECTIONS", "LOGGED_IN"];
  if (!validVisibility.includes(visibility)) {
    return errorResult(
      `Invalid visibility "${visibility}". Must be one of: ${validVisibility.join(", ")}`
    );
  }

  const postText = buildPostText(content, hashtags);
  const templates = loadTemplates();
  const maxChars = templates.post_limits?.max_characters || 3000;

  if (postText.length > maxChars) {
    return errorResult(
      `Post exceeds LinkedIn's ${maxChars}-character limit (${postText.length} chars).`,
      "Shorten the content or reduce hashtags."
    );
  }

  const postId = generatePostId();
  const createdAt = isoNow();

  const postData = {
    id: postId,
    content,
    hashtags,
    visibility,
    post_text: postText,
    created_at: createdAt,
  };

  log("INFO", "create_linkedin_post", {
    post_id: postId,
    visibility,
    char_count: postText.length,
    simulation: SIMULATION_MODE,
  });

  if (SIMULATION_MODE) {
    // SIMULATION: Create approval request file
    let approvalPath;
    try {
      approvalPath = await createApprovalFile(postData);
    } catch (err) {
      return errorResult(`Failed to create approval file: ${err.message}`);
    }

    log("INFO", "SIMULATED post queued for approval", { post_id: postId, approvalPath });

    return successResult({
      mode: "SIMULATION",
      post_id: postId,
      simulated_post_url: `https://www.linkedin.com/feed/update/urn:li:share:SIM_${postId}/`,
      visibility,
      char_count: postText.length,
      char_limit: maxChars,
      hashtags,
      approval_required: true,
      approval_file: path.relative(VAULT_PATH, approvalPath),
      next_steps: [
        `Review approval file: ${path.relative(VAULT_PATH, approvalPath)}`,
        "Move to Approved/ to confirm, or Rejected/ to cancel",
        "In LIVE mode, set SIMULATION_MODE=false and provide LINKEDIN_ACCESS_TOKEN",
      ],
      post_preview: postText,
      created_at: createdAt,
      simulation_note:
        "No real LinkedIn post was created. This is a simulation. " +
        "See README.md for LinkedIn API setup instructions.",
    });
  }

  /* PRODUCTION_ONLY: Remove comment block when SIMULATION_MODE = false
  try {
    const result = await publishToLinkedIn(postText, visibility);
    log("INFO", "post published to LinkedIn", { post_id: postId, post_urn: result.post_urn });
    return successResult({
      mode: "LIVE",
      post_id: postId,
      post_urn: result.post_urn,
      post_url: result.post_url,
      visibility,
      char_count: postText.length,
      hashtags,
      created_at: createdAt,
    });
  } catch (err) {
    log("ERROR", "LinkedIn API publish failed", { error: err.message });
    return errorResult(`LinkedIn publish failed: ${err.message}`, "Check ACCESS_TOKEN and API permissions.");
  }
  */

  return errorResult("SIMULATION_MODE is false but production code is not enabled.");
}

// ----------------------------------------------------------
// 2. schedule_linkedin_post
// ----------------------------------------------------------

/**
 * Queue a LinkedIn post for future publishing.
 *
 * @param {object} args
 * @param {string} args.content        Post body text
 * @param {string} args.scheduled_time ISO 8601 datetime, e.g. "2026-03-01T09:00:00Z"
 * @param {string[]} [args.hashtags]
 * @param {string} [args.visibility]
 * @returns {Promise<object>}
 */
async function scheduleLinkedInPost(args) {
  const {
    content,
    scheduled_time,
    hashtags = [],
    visibility = "PUBLIC",
  } = args;

  if (!content || content.trim().length === 0) {
    return errorResult("'content' is required.");
  }
  if (!scheduled_time) {
    return errorResult("'scheduled_time' is required (ISO 8601 format, e.g. '2026-03-01T09:00:00Z').");
  }

  // Validate scheduled_time
  const scheduledDate = new Date(scheduled_time);
  if (isNaN(scheduledDate.getTime())) {
    return errorResult(
      `Invalid 'scheduled_time': "${scheduled_time}". Use ISO 8601 format.`
    );
  }
  if (scheduledDate <= new Date()) {
    return errorResult(
      "Scheduled time must be in the future.",
      `Provided: ${scheduled_time}. Current time: ${isoNow()}`
    );
  }

  const validVisibility = ["PUBLIC", "CONNECTIONS", "LOGGED_IN"];
  if (!validVisibility.includes(visibility)) {
    return errorResult(
      `Invalid visibility "${visibility}". Must be one of: ${validVisibility.join(", ")}`
    );
  }

  const postText = buildPostText(content, hashtags);
  const templates = loadTemplates();
  const maxChars = templates.post_limits?.max_characters || 3000;

  if (postText.length > maxChars) {
    return errorResult(
      `Post exceeds LinkedIn's ${maxChars}-character limit (${postText.length} chars).`
    );
  }

  const postId = generatePostId();
  const createdAt = isoNow();

  const postData = {
    id: postId,
    content,
    hashtags,
    visibility,
    post_text: postText,
    scheduled_time,
    created_at: createdAt,
  };

  log("INFO", "schedule_linkedin_post", {
    post_id: postId,
    scheduled_time,
    simulation: SIMULATION_MODE,
  });

  let planPath;
  try {
    planPath = await createScheduledPlanFile(postData);
  } catch (err) {
    return errorResult(`Failed to create plan file: ${err.message}`);
  }

  // Time until scheduled
  const msUntil = scheduledDate.getTime() - Date.now();
  const hoursUntil = (msUntil / 3_600_000).toFixed(1);

  return successResult({
    mode: SIMULATION_MODE ? "SIMULATION" : "LIVE",
    post_id: postId,
    scheduled_time,
    hours_until_scheduled: parseFloat(hoursUntil),
    visibility,
    char_count: postText.length,
    hashtags,
    plan_file: path.relative(VAULT_PATH, planPath),
    post_preview: postText,
    created_at: createdAt,
    next_steps: [
      `Plan saved: ${path.relative(VAULT_PATH, planPath)}`,
      `Post will be published at: ${scheduled_time}`,
      SIMULATION_MODE
        ? "SIMULATION: Set SIMULATION_MODE=false to enable real posting"
        : "LIVE: Claude will publish at the scheduled time via LinkedIn API",
    ],
    simulation_note: SIMULATION_MODE
      ? "SIMULATION MODE active. No real LinkedIn post will be created. Plan file saved for reference."
      : null,
  });
}

// ----------------------------------------------------------
// 3. generate_business_content
// ----------------------------------------------------------

/**
 * Generate professional LinkedIn content using templates.
 *
 * @param {object} args
 * @param {string} args.topic          Main topic or subject
 * @param {string} args.post_type      Template type key (announcement, thought_leadership, etc.)
 * @param {string} [args.company_name]
 * @param {string} [args.cta]          Call-to-action text
 * @param {string[]} [args.hashtag_categories] Categories from hashtag_suggestions
 * @returns {Promise<object>}
 */
async function generateBusinessContent(args) {
  const {
    topic,
    post_type,
    company_name = "our company",
    cta = "Share your thoughts in the comments!",
    hashtag_categories = [],
  } = args;

  if (!topic || topic.trim().length === 0) {
    return errorResult("'topic' is required.");
  }
  if (!post_type) {
    return errorResult("'post_type' is required.");
  }

  const templates = loadTemplates();
  const postTypes = templates.post_types || {};
  const validTypes = Object.keys(postTypes);

  if (!postTypes[post_type]) {
    return errorResult(
      `Unknown post_type "${post_type}". Valid types: ${validTypes.join(", ")}`
    );
  }

  const typeConfig = postTypes[post_type];
  const allTemplates = typeConfig.templates || [];

  if (allTemplates.length === 0) {
    return errorResult(`No templates found for post_type "${post_type}".`);
  }

  log("INFO", "generate_business_content", { topic, post_type });

  // Pick a random template from the set
  const templateText =
    allTemplates[Math.floor(Math.random() * allTemplates.length)];

  // Fill in common variable placeholders with the provided topic
  const filled = templateText
    .replace(/\{\{subject\}\}/g, topic)
    .replace(/\{\{topic\}\}/g, topic)
    .replace(/\{\{company\}\}/g, company_name)
    .replace(/\{\{cta\}\}/g, cta)
    .replace(/\{\{action\}\}/g, `master ${topic}`)
    .replace(/\{\{field\}\}/g, topic)
    .replace(/\{\{event_name\}\}/g, topic)
    .replace(/\{\{role\}\}/g, topic)
    .replace(/\{\{milestone\}\}/g, topic)
    // Replace remaining placeholders with descriptive labels for the user to fill
    .replace(/\{\{(\w+)\}\}/g, (_, name) => `[${name.toUpperCase()}]`);

  // Collect suggested hashtags
  const hashtagSuggestions = templates.hashtag_suggestions || {};
  let suggestedHashtags = [];

  // Add hashtags from requested categories
  for (const cat of hashtag_categories) {
    const catTags = hashtagSuggestions[cat] || [];
    suggestedHashtags.push(...catTags);
  }

  // Auto-suggest based on keywords in topic
  const topicLower = topic.toLowerCase();
  if (suggestedHashtags.length === 0) {
    for (const [cat, tags] of Object.entries(hashtagSuggestions)) {
      if (topicLower.includes(cat.replace("_", " ")) || cat.includes(topicLower.split(" ")[0])) {
        suggestedHashtags.push(...tags.slice(0, 3));
      }
    }
    // Always include some general business tags
    if (suggestedHashtags.length < 3) {
      suggestedHashtags.push(...(hashtagSuggestions.business || []).slice(0, 3));
    }
  }

  // Deduplicate and limit to recommended max
  suggestedHashtags = [...new Set(suggestedHashtags)].slice(0, 5);

  const bestPractices = templates.best_practices || [];
  const limits = templates.post_limits || {};

  const charCount = filled.length;
  const variablesNeeded = (filled.match(/\[([A-Z_]+)\]/g) || []).map(
    (v) => v.replace(/[\[\]]/g, "")
  );

  return successResult({
    post_type,
    topic,
    generated_content: filled,
    char_count: charCount,
    char_limit: limits.max_characters || 3000,
    recommended_max: limits.recommended_max || 1300,
    variables_to_fill: variablesNeeded.length > 0 ? variablesNeeded : "none — template is ready to use",
    suggested_hashtags: suggestedHashtags,
    tone: typeConfig.tone || "professional",
    optimal_length: typeConfig.optimal_length || "150-300 words",
    best_practices: bestPractices.slice(0, 4),
    next_steps: [
      variablesNeeded.length > 0
        ? `Fill in placeholder variables: ${variablesNeeded.join(", ")}`
        : "Content is ready — review and personalise",
      `Call create_linkedin_post with this content and hashtags: ${suggestedHashtags.join(", ")}`,
    ],
    all_post_types: validTypes,
    available_hashtag_categories: Object.keys(hashtagSuggestions),
  });
}

// ============================================================
// MCP SERVER SETUP
// ============================================================

const server = new Server(
  {
    name: "linkedin-mcp-server",
    version: "1.0.0",
  },
  {
    capabilities: {
      tools: {},
    },
  }
);

// ------------------------------------------------------------
// List available tools
// ------------------------------------------------------------

server.setRequestHandler(ListToolsRequestSchema, async () => {
  return {
    tools: [
      {
        name: "create_linkedin_post",
        description:
          `Create a LinkedIn post. ${SIMULATION_MODE ? "⚠️ SIMULATION MODE: Creates an approval request in Pending_Approval/ — no real post is published. " : "LIVE MODE: Publishes directly to LinkedIn after creating approval file. "}` +
          "Respects HITL approval workflow per Company Handbook. " +
          "Validates character limits and returns a preview of exactly what will be posted.",
        inputSchema: {
          type: "object",
          properties: {
            content: {
              type: "string",
              description: "Post body text (max 3000 chars). Hook in the first 2 lines is critical.",
            },
            hashtags: {
              type: "array",
              items: { type: "string" },
              description: "Hashtags to append (with or without #). Recommended: 3-5.",
            },
            visibility: {
              type: "string",
              enum: ["PUBLIC", "CONNECTIONS", "LOGGED_IN"],
              description: "Post visibility. Default: PUBLIC.",
            },
          },
          required: ["content"],
        },
      },
      {
        name: "schedule_linkedin_post",
        description:
          "Queue a LinkedIn post for future publishing at a specific time. " +
          "Creates a plan file in Plans/ with the full API payload for reference. " +
          `${SIMULATION_MODE ? "⚠️ SIMULATION MODE active — no real post will be scheduled via LinkedIn." : "LIVE MODE — will publish at the scheduled time."}`,
        inputSchema: {
          type: "object",
          properties: {
            content: {
              type: "string",
              description: "Post body text.",
            },
            scheduled_time: {
              type: "string",
              description: "ISO 8601 future datetime, e.g. '2026-03-01T09:00:00Z'.",
            },
            hashtags: {
              type: "array",
              items: { type: "string" },
              description: "Hashtags to append.",
            },
            visibility: {
              type: "string",
              enum: ["PUBLIC", "CONNECTIONS", "LOGGED_IN"],
              description: "Post visibility. Default: PUBLIC.",
            },
          },
          required: ["content", "scheduled_time"],
        },
      },
      {
        name: "generate_business_content",
        description:
          "Generate professional LinkedIn post content using built-in templates for " +
          "announcements, thought leadership, milestones, tips, events, and hiring posts. " +
          "Suggests relevant hashtags and returns best practices. " +
          "Output can be passed directly to create_linkedin_post.",
        inputSchema: {
          type: "object",
          properties: {
            topic: {
              type: "string",
              description: "Main subject or topic of the post (e.g. 'AI Employee Vault launch', 'remote work tips').",
            },
            post_type: {
              type: "string",
              enum: ["announcement", "thought_leadership", "milestone", "tip", "event", "hiring"],
              description: "Template style to use.",
            },
            company_name: {
              type: "string",
              description: "Company or product name for personalisation. Default: 'our company'.",
            },
            cta: {
              type: "string",
              description: "Call-to-action text for the end of the post.",
            },
            hashtag_categories: {
              type: "array",
              items: {
                type: "string",
                enum: ["technology", "ai_ml", "startup", "software", "business", "career", "marketing", "data", "productivity", "finance"],
              },
              description: "Hashtag category buckets to draw suggestions from.",
            },
          },
          required: ["topic", "post_type"],
        },
      },
    ],
  };
});

// ------------------------------------------------------------
// Handle tool calls
// ------------------------------------------------------------

server.setRequestHandler(CallToolRequestSchema, async (request) => {
  const { name, arguments: args } = request.params;

  log("INFO", `tool called: ${name}`, { simulation_mode: SIMULATION_MODE });

  try {
    switch (name) {
      case "create_linkedin_post":
        return await createLinkedInPost(args);

      case "schedule_linkedin_post":
        return await scheduleLinkedInPost(args);

      case "generate_business_content":
        return await generateBusinessContent(args);

      default:
        return errorResult(
          `Unknown tool: "${name}". Available: create_linkedin_post, schedule_linkedin_post, generate_business_content`
        );
    }
  } catch (err) {
    log("ERROR", `Unhandled error in ${name}`, { error: err.message, stack: err.stack });
    return errorResult(`Internal error in ${name}: ${err.message}`);
  }
});

// ============================================================
// START SERVER
// ============================================================

async function main() {
  const transport = new StdioServerTransport();
  await server.connect(transport);
  log("INFO", "LinkedIn MCP Server started", {
    vault: VAULT_PATH,
    simulation_mode: SIMULATION_MODE,
    note: SIMULATION_MODE
      ? "SIMULATION mode — no real LinkedIn posts will be created"
      : "LIVE mode — real LinkedIn API calls enabled",
  });
}

main().catch((err) => {
  process.stderr.write(`${LOG_PREFIX} FATAL: ${err.message}\n`);
  process.exit(1);
});
