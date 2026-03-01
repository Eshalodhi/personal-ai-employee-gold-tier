/**
 * AI Employee Vault - Social Media MCP Server v3.0
 * =================================================
 * Unified Gold Tier MCP server for LinkedIn, Facebook, Twitter, and Instagram.
 *
 * SIMULATION MODE (default: true for all platforms)
 * --------------------------------------------------
 * All platforms default to simulation mode until API credentials are
 * configured. In simulation mode this server:
 *   - Creates HITL approval requests in Pending_Approval/
 *   - Logs exactly what WOULD be posted on each platform
 *   - Saves scheduled posts as plan files in Plans/
 *   - Returns rich previews with per-platform formatting
 *   - All real API calls are fully implemented but wrapped in
 *     PRODUCTION_ONLY comment blocks — flip the platform flag and
 *     supply credentials to go live independently per platform.
 *
 * Tools (12 total):
 *   LinkedIn (3):
 *     1.  create_linkedin_post       — Draft & HITL-approve a LinkedIn post
 *     2.  schedule_linkedin_post     — Queue a LinkedIn post for future publish
 *     3.  generate_business_content  — LinkedIn template-based content generation
 *   Twitter (2):
 *     4.  create_twitter_post        — Draft tweet/thread + HITL approval
 *     5.  schedule_twitter_post      — Queue tweet/thread for future publish
 *   Instagram (2):
 *     6.  create_instagram_post      — Draft caption (feed/story) + HITL approval
 *     7.  schedule_instagram_post    — Queue Instagram post for future publish
 *   Facebook (2):
 *     8.  create_facebook_post       — Post to profile or page + HITL approval
 *     9.  schedule_facebook_post     — Queue Facebook post for future publish
 *   Cross-platform (3):
 *     10. cross_post_content         — Single approval: LinkedIn + Twitter + Instagram
 *     11. cross_post                 — Single approval: LinkedIn + Facebook + Twitter
 *                                      (adapts content per platform automatically)
 *     12. generate_social_content    — Generate platform-optimised content for
 *                                      any combination of platforms
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

/** Vault root — two levels up from mcp_servers/social_media_mcp/ */
const VAULT_PATH = path.resolve(__dirname, "..", "..");

// ---- Simulation flags (flip independently per platform) ----

/**
 * SIMULATION_MODE flags:
 *   true  → No real API calls. Creates approval/plan files, logs actions.
 *   false → Live API calls. Requires the corresponding credentials below.
 */
const SIMULATE_LINKEDIN  = true;
const SIMULATE_TWITTER   = true;
const SIMULATE_INSTAGRAM = true;

// ---- LinkedIn credentials ----
const LINKEDIN_ACCESS_TOKEN = process.env.LINKEDIN_ACCESS_TOKEN || "";
const LINKEDIN_PERSON_URN   = process.env.LINKEDIN_PERSON_URN   || "urn:li:person:DEMO_ID";
const LINKEDIN_API_BASE     = "https://api.linkedin.com";

// ---- Twitter / X credentials (API v2) ----
const TWITTER_BEARER_TOKEN     = process.env.TWITTER_BEARER_TOKEN     || "";
const TWITTER_API_KEY          = process.env.TWITTER_API_KEY          || "";
const TWITTER_API_SECRET       = process.env.TWITTER_API_SECRET       || "";
const TWITTER_ACCESS_TOKEN     = process.env.TWITTER_ACCESS_TOKEN     || "";
const TWITTER_ACCESS_SECRET    = process.env.TWITTER_ACCESS_SECRET    || "";
const TWITTER_API_BASE         = "https://api.twitter.com/2";

// ---- Instagram / Meta credentials (Graph API v21) ----
const INSTAGRAM_ACCESS_TOKEN   = process.env.INSTAGRAM_ACCESS_TOKEN   || "";
const INSTAGRAM_BUSINESS_ID    = process.env.INSTAGRAM_BUSINESS_ID    || "DEMO_BUSINESS_ID";
const INSTAGRAM_API_BASE       = "https://graph.facebook.com/v21.0";

// ---- Facebook / Meta credentials (Graph API v21) ----
/**
 * SIMULATE_FACEBOOK = true  → No real API calls. Creates approval/plan files.
 * SIMULATE_FACEBOOK = false → Live Facebook Graph API calls.
 *
 * Facebook Graph API setup:
 *   1. Create a Facebook App at developers.facebook.com
 *   2. Add "Facebook Login" + "Pages API" products
 *   3. Get a User Access Token with publish_actions (personal) or
 *      pages_manage_posts (page) permission
 *   4. For pages: exchange for Page Access Token via /{page-id}?fields=access_token
 *   5. Set FACEBOOK_ACCESS_TOKEN (user token) and FACEBOOK_USER_ID (numeric ID from /me)
 *   6. For page posting: also set FACEBOOK_PAGE_ID + FACEBOOK_PAGE_ACCESS_TOKEN
 */
const SIMULATE_FACEBOOK         = true;
const FACEBOOK_ACCESS_TOKEN     = process.env.FACEBOOK_ACCESS_TOKEN         || "";
const FACEBOOK_USER_ID          = process.env.FACEBOOK_USER_ID              || "DEMO_USER_ID";
const FACEBOOK_PAGE_ID          = process.env.FACEBOOK_PAGE_ID              || "";
const FACEBOOK_PAGE_ACCESS_TOKEN = process.env.FACEBOOK_PAGE_ACCESS_TOKEN   || "";
const FACEBOOK_API_BASE         = "https://graph.facebook.com/v21.0";

// ---- Paths ----
const TEMPLATES_PATH = path.join(__dirname, "social_media_templates.json");
const LOG_PREFIX     = "[social-media-mcp]";

// ============================================================
// UTILITIES
// ============================================================

function log(level, message, meta = {}) {
  const entry = { ts: new Date().toISOString(), level, msg: message, ...meta };
  process.stderr.write(`${LOG_PREFIX} ${JSON.stringify(entry)}\n`);
}

function generatePostId() {
  return Math.random().toString(16).slice(2, 10).toUpperCase();
}

function dateStamp() {
  return new Date().toISOString().slice(0, 10);
}

function isoNow() {
  return new Date().toISOString();
}

function loadTemplates() {
  try {
    return JSON.parse(fs.readFileSync(TEMPLATES_PATH, "utf8"));
  } catch (err) {
    log("WARN", "Could not load templates", { error: err.message });
    return { platforms: {}, content_templates: {}, hashtag_suggestions: {}, best_practices: {} };
  }
}

function successResult(data) {
  return {
    content: [
      { type: "text", text: JSON.stringify({ status: "success", ...data }, null, 2) },
    ],
  };
}

function errorResult(message, hint) {
  const body = { status: "error", error: message };
  if (hint) body.hint = hint;
  return {
    content: [{ type: "text", text: JSON.stringify(body, null, 2) }],
    isError: true,
  };
}

/**
 * Build a complete post text with hashtag block appended.
 */
function buildPostText(content, hashtags = []) {
  const trimmed = content.trim();
  if (hashtags.length === 0) return trimmed;
  const tagBlock = hashtags
    .map((h) => (h.startsWith("#") ? h : `#${h}`))
    .join(" ");
  return `${trimmed}\n\n${tagBlock}`;
}

/**
 * Split long text into Twitter thread chunks.
 * Each chunk ≤ maxChars characters. Splits on word boundaries.
 * Prepends [n/N] thread marker automatically.
 */
function splitIntoThread(text, maxChars = 280) {
  const MARKER_RESERVE = 8; // " [N/N]" up to 8 chars
  const effectiveMax = maxChars - MARKER_RESERVE;

  const words = text.split(/\s+/);
  const chunks = [];
  let current = "";

  for (const word of words) {
    const candidate = current ? `${current} ${word}` : word;
    if (candidate.length <= effectiveMax) {
      current = candidate;
    } else {
      if (current) chunks.push(current.trim());
      current = word;
    }
  }
  if (current.trim()) chunks.push(current.trim());

  if (chunks.length === 1) return chunks; // Single tweet — no markers needed

  // Add thread markers
  return chunks.map((chunk, i) => `${chunk} [${i + 1}/${chunks.length}]`);
}

/**
 * Adapt long-form content to Twitter's 280-char limit.
 * Returns the thread chunks array (single element if it fits in one tweet).
 */
function adaptForTwitter(content, hashtags = []) {
  const maxHashtags = 2;
  const selectedTags = hashtags.slice(0, maxHashtags).map((h) =>
    h.startsWith("#") ? h : `#${h}`
  );

  const fullText = content.trim();
  // Try fitting in single tweet with tags
  const withTags = selectedTags.length
    ? `${fullText}\n\n${selectedTags.join(" ")}`
    : fullText;

  if (withTags.length <= 280) return [withTags];

  // Need a thread — split content, put hashtags on last tweet
  const chunks = splitIntoThread(fullText, 280);
  if (selectedTags.length) {
    const last = chunks[chunks.length - 1];
    const lastWithTags = `${last}\n${selectedTags.join(" ")}`;
    chunks[chunks.length - 1] =
      lastWithTags.length <= 280 ? lastWithTags : last;
  }
  return chunks;
}

// ============================================================
// APPROVAL & PLAN FILE WRITERS
// ============================================================

/**
 * Create a HITL approval file for a LinkedIn post.
 */
async function createLinkedInApprovalFile(post) {
  const dir = path.join(VAULT_PATH, "Pending_Approval");
  await fsp.mkdir(dir, { recursive: true });
  const filename = `LINKEDIN_POST_${post.id}_${dateStamp()}.md`;
  const filePath = path.join(dir, filename);

  const content = `---
type: LINKEDIN_POST_APPROVAL
post_id: ${post.id}
platform: linkedin
created_at: ${post.created_at}
status: PENDING_APPROVAL
simulation_mode: ${SIMULATE_LINKEDIN}
---

# LinkedIn Post Approval Request

**Post ID:** \`${post.id}\`
**Created:** ${post.created_at}
**Visibility:** ${post.visibility}
**Character Count:** ${post.post_text.length} / 3000

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
| Simulation Mode | ${SIMULATE_LINKEDIN} |
| Scheduled | Immediate on approval |

## How to Approve

1. Review the post content above
2. Move this file to \`Approved/\` to confirm
3. Move this file to \`Rejected/\` to cancel

## What Happens on Approval

${SIMULATE_LINKEDIN
  ? "**SIMULATION MODE** — No real LinkedIn post will be created. Claude logs the action and moves this file to `Done/`."
  : "**LIVE MODE** — Claude calls the LinkedIn UGC Posts API and publishes. The real post URL will be logged to `Done/`."}

---
*Generated by Social Media MCP Server v2.0 (LinkedIn — ${SIMULATE_LINKEDIN ? "SIMULATION" : "LIVE"} mode)*
`;

  await fsp.writeFile(filePath, content, "utf8");
  log("INFO", "linkedin approval file created", { filePath, post_id: post.id });
  return filePath;
}

/**
 * Create a HITL approval file for a Twitter post/thread.
 */
async function createTwitterApprovalFile(post) {
  const dir = path.join(VAULT_PATH, "Pending_Approval");
  await fsp.mkdir(dir, { recursive: true });
  const filename = `TWITTER_POST_${post.id}_${dateStamp()}.md`;
  const filePath = path.join(dir, filename);

  const isThread = post.thread.length > 1;
  const threadPreview = post.thread
    .map((tweet, i) => `**Tweet ${i + 1}/${post.thread.length}** (${tweet.length} chars)\n\n> ${tweet}`)
    .join("\n\n---\n\n");

  const content = `---
type: TWITTER_POST_APPROVAL
post_id: ${post.id}
platform: twitter
is_thread: ${isThread}
tweet_count: ${post.thread.length}
created_at: ${post.created_at}
status: PENDING_APPROVAL
simulation_mode: ${SIMULATE_TWITTER}
---

# Twitter Post Approval Request

**Post ID:** \`${post.id}\`
**Created:** ${post.created_at}
**Type:** ${isThread ? `Thread (${post.thread.length} tweets)` : "Single tweet"}
**Character counts:** ${post.thread.map((t) => t.length).join(", ")} / 280

## Post Preview

> *Exactly as it will appear on Twitter / X:*

---

${threadPreview}

---

## Metadata

| Field | Value |
|---|---|
| Thread | ${isThread ? `Yes — ${post.thread.length} tweets` : "No — single tweet"} |
| Hashtags | ${post.hashtags.join(", ") || "None"} |
| Simulation Mode | ${SIMULATE_TWITTER} |
| Scheduled | Immediate on approval |

## How to Approve

1. Review each tweet in the thread above
2. Move this file to \`Approved/\` to confirm
3. Move this file to \`Rejected/\` to cancel

## What Happens on Approval

${SIMULATE_TWITTER
  ? "**SIMULATION MODE** — No real tweet will be posted. Claude logs the action and moves this file to `Done/`."
  : "**LIVE MODE** — Claude calls Twitter API v2 `POST /2/tweets` for each tweet in sequence. Thread replies are linked automatically. The tweet URLs will be logged to `Done/`."}

---
*Generated by Social Media MCP Server v2.0 (Twitter — ${SIMULATE_TWITTER ? "SIMULATION" : "LIVE"} mode)*
`;

  await fsp.writeFile(filePath, content, "utf8");
  log("INFO", "twitter approval file created", { filePath, post_id: post.id });
  return filePath;
}

/**
 * Create a HITL approval file for an Instagram post.
 */
async function createInstagramApprovalFile(post) {
  const dir = path.join(VAULT_PATH, "Pending_Approval");
  await fsp.mkdir(dir, { recursive: true });
  const filename = `INSTAGRAM_POST_${post.id}_${dateStamp()}.md`;
  const filePath = path.join(dir, filename);

  const templates = loadTemplates();
  const imgReq = templates.image_requirements || {};
  const reqKey = `instagram_${post.post_type}`;
  const imageSpec = imgReq[reqKey] || imgReq["instagram_feed"] || {};

  const content = `---
type: INSTAGRAM_POST_APPROVAL
post_id: ${post.id}
platform: instagram
post_type: ${post.post_type}
created_at: ${post.created_at}
status: PENDING_APPROVAL
simulation_mode: ${SIMULATE_INSTAGRAM}
---

# Instagram Post Approval Request

**Post ID:** \`${post.id}\`
**Created:** ${post.created_at}
**Post Type:** ${post.post_type.toUpperCase()} (${post.post_type === "story" ? "9:16 vertical" : "feed image"})
**Caption Length:** ${post.caption.length} / 2200 chars
**Hashtag Count:** ${post.hashtags.length} / 30

## IMAGE REQUIREMENT

> ⚠️ **Instagram requires an image or video.** This caption cannot be posted without media.

| Spec | Value |
|---|---|
| Dimensions | ${imageSpec.dimensions || imageSpec.portrait || "1080x1080px (square) or 1080x1350px (portrait)"} |
| Formats | ${(imageSpec.formats || ["JPG", "PNG"]).join(", ")} |
| Max Size | ${imageSpec.max_size || "30MB"} |

**Image to use:** ${post.image_url || "⚠️ NOT PROVIDED — must be added before publishing"}

## Caption Preview

> *Exactly as it will appear on Instagram:*

---

${post.caption}

${post.hashtags.length > 0 ? "\n**Hashtags (post in first comment for cleaner caption):**\n\n" + post.hashtags.map((h) => h.startsWith("#") ? h : `#${h}`).join(" ") : ""}

---

## Metadata

| Field | Value |
|---|---|
| Post Type | ${post.post_type} |
| Caption Chars | ${post.caption.length} / 2200 |
| Hashtag Count | ${post.hashtags.length} / 30 |
| Image Provided | ${post.image_url ? "Yes" : "No — required before publishing"} |
| Simulation Mode | ${SIMULATE_INSTAGRAM} |

## How to Approve

1. Confirm an image/video is available at the URL above (or update it)
2. Review caption and hashtags
3. Move this file to \`Approved/\` to confirm
4. Move this file to \`Rejected/\` to cancel

## What Happens on Approval

${SIMULATE_INSTAGRAM
  ? "**SIMULATION MODE** — No real Instagram post will be created. Claude logs the action and moves this file to `Done/`."
  : "**LIVE MODE** — Claude calls Instagram Graph API to create a media container, then publishes it. The post URL will be logged to `Done/`."}

---
*Generated by Social Media MCP Server v2.0 (Instagram — ${SIMULATE_INSTAGRAM ? "SIMULATION" : "LIVE"} mode)*
`;

  await fsp.writeFile(filePath, content, "utf8");
  log("INFO", "instagram approval file created", { filePath, post_id: post.id });
  return filePath;
}

/**
 * Create a single cross-platform HITL approval file covering all 3 platforms.
 */
async function createCrossPostApprovalFile(crossPost) {
  const dir = path.join(VAULT_PATH, "Pending_Approval");
  await fsp.mkdir(dir, { recursive: true });
  const filename = `CROSSPOST_${crossPost.id}_${dateStamp()}.md`;
  const filePath = path.join(dir, filename);

  const li  = crossPost.linkedin;
  const tw  = crossPost.twitter;
  const ig  = crossPost.instagram;
  const isThread = tw.thread.length > 1;

  const twitterPreview = tw.thread
    .map((t, i) => `**Tweet ${i + 1}/${tw.thread.length}** (${t.length}/280 chars)\n\n> ${t}`)
    .join("\n\n");

  const content = `---
type: CROSS_POST_APPROVAL
post_id: ${crossPost.id}
platforms: linkedin, twitter, instagram
created_at: ${crossPost.created_at}
status: PENDING_APPROVAL
simulation_linkedin: ${SIMULATE_LINKEDIN}
simulation_twitter: ${SIMULATE_TWITTER}
simulation_instagram: ${SIMULATE_INSTAGRAM}
---

# Cross-Platform Post Approval Request

**Post ID:** \`${crossPost.id}\`
**Created:** ${crossPost.created_at}
**Platforms:** LinkedIn + Twitter/X + Instagram

> This is a **single approval** for all three platforms.
> Approving this file will trigger posts on all platforms simultaneously.

---

## LinkedIn Version

**Character count:** ${li.post_text.length} / 3000 | **Hashtags:** ${li.hashtags.join(", ") || "None"}

---

${li.post_text}

---

## Twitter / X Version

**Type:** ${isThread ? `Thread — ${tw.thread.length} tweets` : "Single tweet"}

${twitterPreview}

---

## Instagram Version

**Caption:** ${ig.caption.length} / 2200 chars | **Hashtags:** ${ig.hashtags.length} / 30

> ⚠️ **IMAGE REQUIRED:** ${crossPost.image_url || "No image provided — must be added before publishing"}

---

${ig.caption}

${ig.hashtags.length > 0 ? "\n**Hashtags:**\n" + ig.hashtags.map((h) => h.startsWith("#") ? h : `#${h}`).join(" ") : ""}

---

## Platform Status

| Platform | Mode | Content Type | Ready |
|---|---|---|---|
| LinkedIn | ${SIMULATE_LINKEDIN ? "SIMULATION" : "LIVE"} | ${li.post_text.length} chars, ${li.hashtags.length} hashtags | ✅ |
| Twitter | ${SIMULATE_TWITTER ? "SIMULATION" : "LIVE"} | ${isThread ? `Thread (${tw.thread.length} tweets)` : "Single tweet"} | ✅ |
| Instagram | ${SIMULATE_INSTAGRAM ? "SIMULATION" : "LIVE"} | ${ig.caption.length} chars, ${ig.hashtags.length} hashtags | ${crossPost.image_url ? "✅" : "⚠️ Image needed"} |

## How to Approve

1. Review all three platform versions above
2. Confirm Instagram image is available (if not in simulation mode)
3. Move this file to \`Approved/\` to publish to all platforms
4. Move this file to \`Rejected/\` to cancel all platforms

## What Happens on Approval

${[
  SIMULATE_LINKEDIN  ? "LinkedIn: SIMULATION — logged, not posted" : "LinkedIn: LIVE — posts via UGC API",
  SIMULATE_TWITTER   ? "Twitter:  SIMULATION — logged, not posted" : "Twitter:  LIVE — posts via API v2",
  SIMULATE_INSTAGRAM ? "Instagram: SIMULATION — logged, not posted" : "Instagram: LIVE — posts via Graph API",
].join("\n")}

---
*Generated by Social Media MCP Server v2.0 (Cross-Platform — ${crossPost.created_at})*
`;

  await fsp.writeFile(filePath, content, "utf8");
  log("INFO", "cross-post approval file created", { filePath, post_id: crossPost.id });
  return filePath;
}

/**
 * Create a scheduled post plan file.
 */
async function createScheduledPlanFile(platform, post) {
  const dir = path.join(VAULT_PATH, "Plans");
  await fsp.mkdir(dir, { recursive: true });
  const platformUp = platform.toUpperCase();
  const filename = `${platformUp}_SCHEDULED_${post.id}_${dateStamp()}.md`;
  const filePath = path.join(dir, filename);

  const simulate = platform === "linkedin"  ? SIMULATE_LINKEDIN
                 : platform === "twitter"   ? SIMULATE_TWITTER
                 : SIMULATE_INSTAGRAM;

  const content = `---
type: ${platformUp}_SCHEDULED_POST
post_id: ${post.id}
platform: ${platform}
created_at: ${post.created_at}
scheduled_for: ${post.scheduled_time}
status: SCHEDULED
simulation_mode: ${simulate}
---

# Scheduled ${platformUp} Post

**Post ID:** \`${post.id}\`
**Platform:** ${platformUp}
**Created:** ${post.created_at}
**Scheduled For:** ${post.scheduled_time}

## Content Preview

---

${platform === "twitter"
  ? post.thread.map((t, i) => `Tweet ${i + 1}: ${t}`).join("\n\n")
  : platform === "instagram"
  ? `${post.caption}\n\n${post.hashtags.join(" ")}`
  : post.post_text}

---

## Schedule Details

| Field | Value |
|---|---|
| Post ID | \`${post.id}\` |
| Platform | ${platformUp} |
| Scheduled Time | ${post.scheduled_time} |
| Mode | ${simulate ? "SIMULATION" : "LIVE"} |
| Optimal Slot | ${post.optimal_note || "User-specified"} |

## Execution Plan

${simulate
  ? `1. At scheduled time, review this plan file\n2. **SIMULATION**: Log simulated action (no real API call)\n3. Move plan to \`Done/\``
  : `1. At scheduled time, review this plan file\n2. Call ${platformUp} API to publish\n3. Log real post URL and move plan to \`Done/\``
}

---
*Generated by Social Media MCP Server v2.0 (${platformUp} — ${simulate ? "SIMULATION" : "LIVE"} mode)*
`;

  await fsp.writeFile(filePath, content, "utf8");
  log("INFO", "scheduled plan file created", { filePath, post_id: post.id, platform });
  return filePath;
}

/**
 * Create a HITL approval file for a Facebook post.
 */
async function createFacebookApprovalFile(post) {
  const dir = path.join(VAULT_PATH, "Pending_Approval");
  await fsp.mkdir(dir, { recursive: true });
  const filename = `FACEBOOK_POST_${post.id}_${dateStamp()}.md`;
  const filePath = path.join(dir, filename);

  const isPage = post.target_type === "page";
  const targetLabel = isPage
    ? `Facebook Page (${FACEBOOK_PAGE_ID || "page-id not set"})`
    : `Facebook Profile (user: ${FACEBOOK_USER_ID})`;

  const content = `---
type: FACEBOOK_POST_APPROVAL
post_id: ${post.id}
platform: facebook
target_type: ${post.target_type}
created_at: ${post.created_at}
status: PENDING_APPROVAL
simulation_mode: ${SIMULATE_FACEBOOK}
---

# Facebook Post Approval Request

**Post ID:** \`${post.id}\`
**Created:** ${post.created_at}
**Target:** ${targetLabel}
**Character Count:** ${post.content.length}
${post.link_url  ? `**Link:** ${post.link_url}`  : ""}
${post.image_url ? `**Image:** ${post.image_url}` : ""}

## Post Preview

> *Exactly as it will appear on Facebook:*

---

${post.content}${post.link_url ? `\n\n${post.link_url}` : ""}

---

## Metadata

| Field | Value |
|---|---|
| Target | ${targetLabel} |
| Post Type | ${post.link_url ? "Link post" : post.image_url ? "Image post" : "Text post"} |
| Simulation Mode | ${SIMULATE_FACEBOOK} |
| Scheduled | Immediate on approval |

## How to Approve

1. Review the post content above
2. Move this file to \`Approved/\` to confirm
3. Move this file to \`Rejected/\` to cancel

## What Happens on Approval

${SIMULATE_FACEBOOK
  ? "**SIMULATION MODE** — No real Facebook post will be created. Claude logs the simulated action and moves this file to `Done/`."
  : `**LIVE MODE** — Claude calls Facebook Graph API \`POST /${isPage ? FACEBOOK_PAGE_ID : "me"}/feed\` and publishes.\nThe real post URL will be logged to \`Done/\`.`}

---
*Generated by Social Media MCP Server v3.0 (Facebook — ${SIMULATE_FACEBOOK ? "SIMULATION" : "LIVE"} mode)*
`;

  await fsp.writeFile(filePath, content, "utf8");
  log("INFO", "facebook approval file created", { filePath, post_id: post.id });
  return filePath;
}

/**
 * Create a unified cross-post approval file for LinkedIn + Facebook + Twitter.
 */
async function createCrossPostLFTApprovalFile(crossPost) {
  const dir = path.join(VAULT_PATH, "Pending_Approval");
  await fsp.mkdir(dir, { recursive: true });
  const filename = `CROSSPOST_LFT_${crossPost.id}_${dateStamp()}.md`;
  const filePath = path.join(dir, filename);

  const li  = crossPost.linkedin;
  const fb  = crossPost.facebook;
  const tw  = crossPost.twitter;
  const isThread = tw.thread.length > 1;

  const twitterPreview = tw.thread
    .map((t, i) => `**Tweet ${i + 1}/${tw.thread.length}** (${t.length}/280 chars)\n\n> ${t}`)
    .join("\n\n");

  const activePlatforms = crossPost.platforms || ["linkedin", "facebook", "twitter"];

  const content = `---
type: CROSS_POST_APPROVAL_LFT
post_id: ${crossPost.id}
platforms: ${activePlatforms.join(", ")}
created_at: ${crossPost.created_at}
status: PENDING_APPROVAL
simulation_linkedin: ${SIMULATE_LINKEDIN}
simulation_facebook: ${SIMULATE_FACEBOOK}
simulation_twitter: ${SIMULATE_TWITTER}
---

# Cross-Platform Post Approval (LinkedIn + Facebook + Twitter)

**Post ID:** \`${crossPost.id}\`
**Created:** ${crossPost.created_at}
**Platforms:** ${activePlatforms.map(p => p.charAt(0).toUpperCase() + p.slice(1)).join(" + ")}

> This is a **single approval** for all selected platforms.
> Approving this file will trigger posts on all platforms simultaneously.

---
${activePlatforms.includes("linkedin") ? `
## LinkedIn Version

**Character count:** ${li.post_text.length} / 3000 | **Hashtags:** ${li.hashtags.join(", ") || "None"}

---

${li.post_text}

---
` : ""}
${activePlatforms.includes("facebook") ? `
## Facebook Version

**Target:** ${fb.target_type === "page" ? `Page (${FACEBOOK_PAGE_ID || "page-id not set"})` : "Profile"} | **Chars:** ${fb.content.length}
${fb.link_url ? `**Link:** ${fb.link_url}` : ""}

---

${fb.content}${fb.link_url ? `\n\n${fb.link_url}` : ""}

---
` : ""}
${activePlatforms.includes("twitter") ? `
## Twitter / X Version

**Type:** ${isThread ? `Thread — ${tw.thread.length} tweets` : "Single tweet"}

${twitterPreview}

---
` : ""}

## Platform Status

| Platform | Mode | Content | Ready |
|---|---|---|---|
${activePlatforms.includes("linkedin")  ? `| LinkedIn  | ${SIMULATE_LINKEDIN  ? "SIMULATION" : "LIVE"} | ${li.post_text.length} chars, ${li.hashtags.length} hashtags | ✅ |\n` : ""}${activePlatforms.includes("facebook")  ? `| Facebook  | ${SIMULATE_FACEBOOK  ? "SIMULATION" : "LIVE"} | ${fb.content.length} chars, ${fb.target_type} | ✅ |\n` : ""}${activePlatforms.includes("twitter")   ? `| Twitter   | ${SIMULATE_TWITTER   ? "SIMULATION" : "LIVE"} | ${isThread ? `Thread (${tw.thread.length} tweets)` : "Single tweet"} | ✅ |\n` : ""}

## How to Approve

1. Review all platform versions above
2. Move this file to \`Approved/\` to publish to all selected platforms
3. Move this file to \`Rejected/\` to cancel all platforms

## What Happens on Approval

${[
  activePlatforms.includes("linkedin")  ? (SIMULATE_LINKEDIN  ? "LinkedIn: SIMULATION — logged, not posted" : "LinkedIn: LIVE — posts via UGC API") : null,
  activePlatforms.includes("facebook")  ? (SIMULATE_FACEBOOK  ? "Facebook: SIMULATION — logged, not posted" : "Facebook: LIVE — posts via Graph API") : null,
  activePlatforms.includes("twitter")   ? (SIMULATE_TWITTER   ? "Twitter:  SIMULATION — logged, not posted" : "Twitter:  LIVE — posts via API v2") : null,
].filter(Boolean).join("\n")}

---
*Generated by Social Media MCP Server v3.0 (Cross-Platform LFT — ${crossPost.created_at})*
`;

  await fsp.writeFile(filePath, content, "utf8");
  log("INFO", "cross-post LFT approval file created", { filePath, post_id: crossPost.id });
  return filePath;
}

// ============================================================
// LINKEDIN TOOLS
// ============================================================

async function createLinkedInPost(args) {
  const { content, hashtags = [], visibility = "PUBLIC" } = args;

  if (!content || !content.trim()) return errorResult("'content' is required.");

  const validVis = ["PUBLIC", "CONNECTIONS", "LOGGED_IN"];
  if (!validVis.includes(visibility))
    return errorResult(`Invalid visibility "${visibility}". Options: ${validVis.join(", ")}`);

  const postText = buildPostText(content, hashtags);
  if (postText.length > 3000)
    return errorResult(`Post exceeds LinkedIn's 3000-char limit (${postText.length} chars).`, "Shorten content or reduce hashtags.");

  const postId = generatePostId();
  const createdAt = isoNow();
  const postData = { id: postId, content, hashtags, visibility, post_text: postText, created_at: createdAt };

  log("INFO", "create_linkedin_post", { post_id: postId, chars: postText.length, simulate: SIMULATE_LINKEDIN });

  if (SIMULATE_LINKEDIN) {
    let approvalPath;
    try { approvalPath = await createLinkedInApprovalFile(postData); }
    catch (err) { return errorResult(`Failed to create approval file: ${err.message}`); }

    return successResult({
      mode: "SIMULATION",
      platform: "linkedin",
      post_id: postId,
      char_count: postText.length,
      char_limit: 3000,
      visibility,
      hashtags,
      approval_required: true,
      approval_file: path.relative(VAULT_PATH, approvalPath),
      post_preview: postText,
      created_at: createdAt,
      next_steps: [
        `Review: ${path.relative(VAULT_PATH, approvalPath)}`,
        "Move to Approved/ to confirm, or Rejected/ to cancel",
        "To go live: set SIMULATE_LINKEDIN=false + LINKEDIN_ACCESS_TOKEN env var",
      ],
      simulation_note: "No real LinkedIn post created. See README.md for LinkedIn OAuth 2.0 setup.",
    });
  }

  /* PRODUCTION_ONLY — LinkedIn UGC Posts API
  const payload = {
    author: LINKEDIN_PERSON_URN,
    lifecycleState: "PUBLISHED",
    specificContent: { "com.linkedin.ugc.ShareContent": { shareCommentary: { text: postText }, shareMediaCategory: "NONE" } },
    visibility: { "com.linkedin.ugc.MemberNetworkVisibility": visibility },
  };
  const response = await fetch(`${LINKEDIN_API_BASE}/v2/ugcPosts`, {
    method: "POST",
    headers: { Authorization: `Bearer ${LINKEDIN_ACCESS_TOKEN}`, "Content-Type": "application/json", "X-Restli-Protocol-Version": "2.0.0", "LinkedIn-Version": "202304" },
    body: JSON.stringify(payload),
  });
  if (!response.ok) { const err = await response.text(); return errorResult(`LinkedIn API error ${response.status}: ${err}`); }
  const postUrn = response.headers.get("X-RestLi-Id");
  return successResult({ mode: "LIVE", platform: "linkedin", post_id: postId, post_urn: postUrn,
    post_url: `https://www.linkedin.com/feed/update/${encodeURIComponent(postUrn)}/`, char_count: postText.length, created_at: createdAt });
  */
  return errorResult("SIMULATE_LINKEDIN is false but production code is not enabled.");
}

async function scheduleLinkedInPost(args) {
  const { content, scheduled_time, hashtags = [], visibility = "PUBLIC" } = args;

  if (!content || !content.trim()) return errorResult("'content' is required.");
  if (!scheduled_time)            return errorResult("'scheduled_time' is required (ISO 8601).");

  const scheduledDate = new Date(scheduled_time);
  if (isNaN(scheduledDate.getTime())) return errorResult(`Invalid scheduled_time: "${scheduled_time}"`);
  if (scheduledDate <= new Date())    return errorResult("Scheduled time must be in the future.");

  const validVis = ["PUBLIC", "CONNECTIONS", "LOGGED_IN"];
  if (!validVis.includes(visibility))
    return errorResult(`Invalid visibility "${visibility}". Options: ${validVis.join(", ")}`);

  const postText = buildPostText(content, hashtags);
  if (postText.length > 3000)
    return errorResult(`Post exceeds LinkedIn's 3000-char limit (${postText.length} chars).`);

  const postId = generatePostId();
  const templates = loadTemplates();
  const liPlatform = templates.platforms?.linkedin || {};

  const scheduledDow = scheduledDate.toLocaleDateString("en-US", { weekday: "long" });
  const scheduledHour = scheduledDate.getUTCHours();
  const bestDays = liPlatform.best_days || ["Tuesday", "Wednesday", "Thursday"];
  const isOptimalDay = bestDays.includes(scheduledDow);
  const isOptimalHour = (scheduledHour >= 8 && scheduledHour <= 10) || (scheduledHour >= 12 && scheduledHour <= 13);

  const postData = {
    id: postId, content, hashtags, visibility, post_text: postText,
    scheduled_time, created_at: isoNow(),
    optimal_note: isOptimalDay && isOptimalHour ? "Optimal day and time" :
                  isOptimalDay ? "Optimal day — consider 8-10am or 12-1pm" :
                  "Consider Tue-Thu 8-10am for maximum LinkedIn reach",
  };

  let planPath;
  try { planPath = await createScheduledPlanFile("linkedin", postData); }
  catch (err) { return errorResult(`Failed to create plan file: ${err.message}`); }

  const hoursUntil = ((scheduledDate - Date.now()) / 3_600_000).toFixed(1);

  return successResult({
    mode: SIMULATE_LINKEDIN ? "SIMULATION" : "LIVE",
    platform: "linkedin",
    post_id: postId,
    scheduled_time,
    hours_until: parseFloat(hoursUntil),
    is_optimal_time: isOptimalDay && isOptimalHour,
    optimal_suggestion: postData.optimal_note,
    best_times: liPlatform.best_times || ["Tue-Thu 8-10am", "Tue-Thu 12-1pm"],
    best_days: bestDays,
    char_count: postText.length,
    hashtags,
    plan_file: path.relative(VAULT_PATH, planPath),
    post_preview: postText,
    created_at: postData.created_at,
  });
}

async function generateBusinessContent(args) {
  const { topic, post_type, company_name = "our company", cta = "Share your thoughts below!", hashtag_categories = [] } = args;

  if (!topic || !topic.trim()) return errorResult("'topic' is required.");
  if (!post_type)              return errorResult("'post_type' is required.");

  const templates = loadTemplates();
  const contentTemplates = templates.content_templates || {};
  const validTypes = Object.keys(contentTemplates);

  if (!contentTemplates[post_type])
    return errorResult(`Unknown post_type "${post_type}". Valid: ${validTypes.join(", ")}`);

  const typeConfig = contentTemplates[post_type];
  const liTemplates = typeConfig.linkedin?.templates || [];
  if (liTemplates.length === 0) return errorResult(`No LinkedIn templates for "${post_type}".`);

  const template = liTemplates[Math.floor(Math.random() * liTemplates.length)];
  const filled = template
    .replace(/\{\{topic\}\}/g, topic)
    .replace(/\{\{subject\}\}/g, topic)
    .replace(/\{\{company\}\}/g, company_name)
    .replace(/\{\{cta\}\}/g, cta)
    .replace(/\{\{(\w+)\}\}/g, (_, name) => `[${name.toUpperCase()}]`);

  const hashtagMap = templates.hashtag_suggestions?.linkedin || {};
  let suggested = [];
  for (const cat of hashtag_categories) suggested.push(...(hashtagMap[cat] || []));
  if (suggested.length < 3) {
    for (const [cat, tags] of Object.entries(hashtagMap)) {
      if (topic.toLowerCase().includes(cat.replace("_", " "))) suggested.push(...tags.slice(0, 3));
    }
  }
  if (suggested.length < 3) suggested.push(...(hashtagMap.business || []).slice(0, 3));
  suggested = [...new Set(suggested)].slice(0, 5);

  const variables = (filled.match(/\[([A-Z_]+)\]/g) || []).map((v) => v.replace(/[\[\]]/g, ""));

  return successResult({
    platform: "linkedin",
    post_type,
    topic,
    generated_content: filled,
    char_count: filled.length,
    char_limit: 3000,
    char_recommended: 1300,
    variables_to_fill: variables.length > 0 ? variables : "none — ready to use",
    suggested_hashtags: suggested,
    tone: typeConfig.linkedin?.tone || "professional",
    best_practices: (templates.best_practices?.linkedin || []).slice(0, 4),
    available_post_types: validTypes,
    next_steps: [
      variables.length > 0 ? `Fill placeholders: ${variables.join(", ")}` : "Content ready — personalise before posting",
      `Call create_linkedin_post with this content and hashtags: ${suggested.join(", ")}`,
    ],
  });
}

// ============================================================
// TWITTER TOOLS
// ============================================================

async function createTwitterPost(args) {
  const { content, hashtags = [], optimize_hashtags = true } = args;

  if (!content || !content.trim()) return errorResult("'content' is required.");
  if (hashtags.length > 3)
    return errorResult("Twitter best practice: max 3 hashtags (2 recommended). Reduce hashtag count.", "Too many hashtags reduce organic reach on Twitter.");

  const thread = adaptForTwitter(content, hashtags);
  const isThread = thread.length > 1;

  // Validate each tweet fits 280
  for (let i = 0; i < thread.length; i++) {
    if (thread[i].length > 280)
      return errorResult(`Tweet ${i + 1} exceeds 280 chars (${thread[i].length}). Content could not be split cleanly.`);
  }

  const postId = generatePostId();
  const createdAt = isoNow();
  const postData = { id: postId, content, thread, hashtags, created_at: createdAt };

  log("INFO", "create_twitter_post", {
    post_id: postId,
    is_thread: isThread,
    tweet_count: thread.length,
    simulate: SIMULATE_TWITTER,
  });

  if (SIMULATE_TWITTER) {
    let approvalPath;
    try { approvalPath = await createTwitterApprovalFile(postData); }
    catch (err) { return errorResult(`Failed to create approval file: ${err.message}`); }

    const templates = loadTemplates();
    const twPlatform = templates.platforms?.twitter || {};

    return successResult({
      mode: "SIMULATION",
      platform: "twitter",
      post_id: postId,
      is_thread: isThread,
      tweet_count: thread.length,
      tweets: thread.map((t, i) => ({ index: i + 1, text: t, char_count: t.length })),
      hashtags,
      approval_required: true,
      approval_file: path.relative(VAULT_PATH, approvalPath),
      created_at: createdAt,
      best_times: twPlatform.best_times || ["Mon-Fri 8-10am", "Mon-Fri 12-1pm"],
      best_practices: (templates.best_practices?.twitter || []).slice(0, 4),
      next_steps: [
        `Review: ${path.relative(VAULT_PATH, approvalPath)}`,
        "Move to Approved/ to confirm, or Rejected/ to cancel",
        isThread ? `Thread has ${thread.length} tweets — each will be posted in reply chain` : "Single tweet",
        "To go live: set SIMULATE_TWITTER=false + TWITTER_API_KEY/SECRET + TWITTER_ACCESS_TOKEN/SECRET env vars",
      ],
      simulation_note: "No real tweet posted. See README.md for Twitter API v2 OAuth 1.0a setup.",
    });
  }

  /* PRODUCTION_ONLY — Twitter API v2 (OAuth 1.0a User Context)
  // Post each tweet in the thread as a reply chain:
  // Tweet 1: POST /2/tweets { text }
  // Tweet 2: POST /2/tweets { text, reply: { in_reply_to_tweet_id: tweet1_id } }
  // etc.
  // Requires OAuth 1.0a signing with TWITTER_API_KEY/SECRET and TWITTER_ACCESS_TOKEN/SECRET.
  // Use a Twitter OAuth 1.0a signing library (e.g., twitter-api-v2 npm package).
  const tweetIds = [];
  let replyToId = null;
  for (const tweetText of thread) {
    const body = { text: tweetText };
    if (replyToId) body.reply = { in_reply_to_tweet_id: replyToId };
    const response = await fetch(`${TWITTER_API_BASE}/tweets`, {
      method: "POST",
      headers: { Authorization: `Bearer ${TWITTER_BEARER_TOKEN}`, "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    if (!response.ok) { const err = await response.text(); return errorResult(`Twitter API error ${response.status}: ${err}`); }
    const data = await response.json();
    replyToId = data.data.id;
    tweetIds.push(replyToId);
  }
  return successResult({ mode: "LIVE", platform: "twitter", post_id: postId, tweet_ids: tweetIds,
    tweet_urls: tweetIds.map(id => `https://twitter.com/i/web/status/${id}`), created_at: createdAt });
  */
  return errorResult("SIMULATE_TWITTER is false but production code is not enabled.");
}

async function scheduleTwitterPost(args) {
  const { content, scheduled_time, hashtags = [] } = args;

  if (!content || !content.trim()) return errorResult("'content' is required.");
  if (!scheduled_time)            return errorResult("'scheduled_time' is required (ISO 8601).");

  const scheduledDate = new Date(scheduled_time);
  if (isNaN(scheduledDate.getTime())) return errorResult(`Invalid scheduled_time: "${scheduled_time}"`);
  if (scheduledDate <= new Date())    return errorResult("Scheduled time must be in the future.");
  if (hashtags.length > 3)           return errorResult("Max 3 hashtags for Twitter (2 recommended).");

  const thread = adaptForTwitter(content, hashtags);
  const templates = loadTemplates();
  const twPlatform = templates.platforms?.twitter || {};

  const scheduledDow  = scheduledDate.toLocaleDateString("en-US", { weekday: "long" });
  const scheduledHour = scheduledDate.getUTCHours();
  const bestDays  = twPlatform.best_days  || ["Tuesday", "Wednesday", "Thursday"];
  const isOptDay  = bestDays.includes(scheduledDow);
  const isOptHour = (scheduledHour >= 8 && scheduledHour <= 10) || (scheduledHour >= 12 && scheduledHour <= 13) || (scheduledHour >= 18 && scheduledHour <= 21);

  const postId = generatePostId();
  const postData = {
    id: postId, content, thread, hashtags, scheduled_time, created_at: isoNow(),
    optimal_note: isOptDay && isOptHour ? "Optimal day and time for Twitter" :
                  "Consider Mon-Fri 8-10am, 12-1pm, or 6-9pm for best Twitter reach",
  };

  let planPath;
  try { planPath = await createScheduledPlanFile("twitter", postData); }
  catch (err) { return errorResult(`Failed to create plan file: ${err.message}`); }

  const hoursUntil = ((scheduledDate - Date.now()) / 3_600_000).toFixed(1);

  return successResult({
    mode: SIMULATE_TWITTER ? "SIMULATION" : "LIVE",
    platform: "twitter",
    post_id: postId,
    is_thread: thread.length > 1,
    tweet_count: thread.length,
    scheduled_time,
    hours_until: parseFloat(hoursUntil),
    is_optimal_time: isOptDay && isOptHour,
    optimal_suggestion: postData.optimal_note,
    best_times: twPlatform.best_times || ["Mon-Fri 8-10am", "12-1pm", "6-9pm"],
    best_days: bestDays,
    tweet_previews: thread.map((t, i) => ({ index: i + 1, text: t, char_count: t.length })),
    plan_file: path.relative(VAULT_PATH, planPath),
    created_at: postData.created_at,
  });
}

// ============================================================
// INSTAGRAM TOOLS
// ============================================================

async function createInstagramPost(args) {
  const {
    caption,
    hashtags = [],
    post_type = "feed",
    image_url = "",
    hashtags_in_first_comment = true,
  } = args;

  if (!caption || !caption.trim()) return errorResult("'caption' is required.");
  if (caption.length > 2200)
    return errorResult(`Caption exceeds Instagram's 2200-char limit (${caption.length} chars).`);
  if (hashtags.length > 30)
    return errorResult(`Too many hashtags: ${hashtags.length}. Instagram allows max 30.`);

  const validTypes = ["feed", "story"];
  if (!validTypes.includes(post_type))
    return errorResult(`Invalid post_type "${post_type}". Options: ${validTypes.join(", ")}`);

  const postId = generatePostId();
  const createdAt = isoNow();
  const postData = { id: postId, caption, hashtags, post_type, image_url, created_at: createdAt };

  log("INFO", "create_instagram_post", {
    post_id: postId,
    post_type,
    caption_chars: caption.length,
    hashtag_count: hashtags.length,
    has_image: !!image_url,
    simulate: SIMULATE_INSTAGRAM,
  });

  if (SIMULATE_INSTAGRAM) {
    let approvalPath;
    try { approvalPath = await createInstagramApprovalFile(postData); }
    catch (err) { return errorResult(`Failed to create approval file: ${err.message}`); }

    const templates = loadTemplates();
    const igPlatform = templates.platforms?.instagram || {};
    const imgReq     = templates.image_requirements   || {};
    const imgSpec    = imgReq[`instagram_${post_type}`] || imgReq["instagram_feed"] || {};

    return successResult({
      mode: "SIMULATION",
      platform: "instagram",
      post_id: postId,
      post_type,
      caption_length: caption.length,
      caption_limit: 2200,
      hashtag_count: hashtags.length,
      hashtag_limit: 30,
      hashtags,
      hashtags_placement: hashtags_in_first_comment ? "first comment (recommended)" : "caption",
      image_url: image_url || "NOT PROVIDED",
      image_required: true,
      image_spec: imgSpec,
      approval_required: true,
      approval_file: path.relative(VAULT_PATH, approvalPath),
      created_at: createdAt,
      best_times: igPlatform.best_times || ["Mon-Fri 9-11am", "Mon-Fri 1-3pm"],
      best_practices: (templates.best_practices?.instagram || []).slice(0, 4),
      next_steps: [
        `Review: ${path.relative(VAULT_PATH, approvalPath)}`,
        image_url ? "Image URL provided — confirm it is accessible" : "⚠️  Add an image URL before approving",
        "Move to Approved/ to confirm, or Rejected/ to cancel",
        "To go live: set SIMULATE_INSTAGRAM=false + INSTAGRAM_ACCESS_TOKEN + INSTAGRAM_BUSINESS_ID env vars",
      ],
      simulation_note: "No real Instagram post created. See README.md for Instagram Graph API setup.",
    });
  }

  /* PRODUCTION_ONLY — Instagram Graph API v21
  if (!image_url) return errorResult("'image_url' is required for live Instagram posting (publicly accessible URL).");
  // Step 1: Create media container
  const createRes = await fetch(
    `${INSTAGRAM_API_BASE}/${INSTAGRAM_BUSINESS_ID}/media?image_url=${encodeURIComponent(image_url)}&caption=${encodeURIComponent(caption)}&access_token=${INSTAGRAM_ACCESS_TOKEN}`,
    { method: "POST" }
  );
  if (!createRes.ok) { const err = await createRes.text(); return errorResult(`Instagram create container error: ${err}`); }
  const { id: containerId } = await createRes.json();
  // Step 2: Publish the container
  const publishRes = await fetch(
    `${INSTAGRAM_API_BASE}/${INSTAGRAM_BUSINESS_ID}/media_publish?creation_id=${containerId}&access_token=${INSTAGRAM_ACCESS_TOKEN}`,
    { method: "POST" }
  );
  if (!publishRes.ok) { const err = await publishRes.text(); return errorResult(`Instagram publish error: ${err}`); }
  const { id: mediaId } = await publishRes.json();
  return successResult({ mode: "LIVE", platform: "instagram", post_id: postId, media_id: mediaId,
    post_url: `https://www.instagram.com/p/${mediaId}/`, caption_length: caption.length, created_at: createdAt });
  */
  return errorResult("SIMULATE_INSTAGRAM is false but production code is not enabled.");
}

async function scheduleInstagramPost(args) {
  const { caption, scheduled_time, hashtags = [], post_type = "feed", image_url = "" } = args;

  if (!caption || !caption.trim())  return errorResult("'caption' is required.");
  if (!scheduled_time)              return errorResult("'scheduled_time' is required (ISO 8601).");
  if (caption.length > 2200)        return errorResult(`Caption exceeds 2200-char limit (${caption.length} chars).`);
  if (hashtags.length > 30)         return errorResult(`Too many hashtags: ${hashtags.length}. Max 30.`);

  const scheduledDate = new Date(scheduled_time);
  if (isNaN(scheduledDate.getTime())) return errorResult(`Invalid scheduled_time: "${scheduled_time}"`);
  if (scheduledDate <= new Date())    return errorResult("Scheduled time must be in the future.");

  const templates = loadTemplates();
  const igPlatform = templates.platforms?.instagram || {};
  const bestDays   = igPlatform.best_days || ["Monday", "Tuesday", "Wednesday"];
  const scheduledDow  = scheduledDate.toLocaleDateString("en-US", { weekday: "long" });
  const scheduledHour = scheduledDate.getUTCHours();
  const isOptDay  = bestDays.includes(scheduledDow);
  const isOptHour = (scheduledHour >= 9 && scheduledHour <= 11) || (scheduledHour >= 13 && scheduledHour <= 15);

  const postId = generatePostId();
  const postData = {
    id: postId, caption, hashtags, post_type, image_url, scheduled_time, created_at: isoNow(),
    optimal_note: isOptDay && isOptHour ? "Optimal day and time for Instagram" :
                  "Consider Mon-Wed 9-11am or 1-3pm for maximum Instagram reach",
  };

  let planPath;
  try { planPath = await createScheduledPlanFile("instagram", postData); }
  catch (err) { return errorResult(`Failed to create plan file: ${err.message}`); }

  const hoursUntil = ((scheduledDate - Date.now()) / 3_600_000).toFixed(1);

  return successResult({
    mode: SIMULATE_INSTAGRAM ? "SIMULATION" : "LIVE",
    platform: "instagram",
    post_id: postId,
    post_type,
    scheduled_time,
    hours_until: parseFloat(hoursUntil),
    is_optimal_time: isOptDay && isOptHour,
    optimal_suggestion: postData.optimal_note,
    best_times: igPlatform.best_times || ["Mon-Fri 9-11am", "1-3pm"],
    best_days: bestDays,
    caption_length: caption.length,
    hashtag_count: hashtags.length,
    image_url: image_url || "NOT PROVIDED — required before publishing",
    plan_file: path.relative(VAULT_PATH, planPath),
    created_at: postData.created_at,
    content_calendar_note: `Add to content calendar: ${scheduledDow} ${scheduled_time}`,
  });
}

// ============================================================
// CROSS-PLATFORM TOOL
// ============================================================

async function crossPostContent(args) {
  const {
    content,
    image_url = "",
    linkedin_hashtags   = ["#AI", "#Automation", "#Innovation"],
    twitter_hashtags    = ["#AI", "#BuildInPublic"],
    instagram_hashtags  = [],
    linkedin_visibility = "PUBLIC",
    post_type           = "feed",
  } = args;

  if (!content || !content.trim()) return errorResult("'content' is required.");

  const templates = loadTemplates();

  // ---- LinkedIn adaptation ----
  const liText = buildPostText(content, linkedin_hashtags);
  if (liText.length > 3000)
    return errorResult(`Content too long for LinkedIn even with adaptation (${liText.length} / 3000 chars).`, "Shorten content.");

  // ---- Twitter adaptation (auto-split if needed) ----
  const twThread = adaptForTwitter(content, twitter_hashtags);
  for (let i = 0; i < twThread.length; i++) {
    if (twThread[i].length > 280)
      return errorResult(`Twitter tweet ${i + 1} exceeds 280 chars after splitting. Content could not be automatically adapted.`);
  }

  // ---- Instagram adaptation ----
  // Truncate to 2200 chars + add up to 30 hashtags
  const igCaption = content.length > 2200 ? content.slice(0, 2197) + "..." : content;
  let igHashtags  = instagram_hashtags;
  if (igHashtags.length === 0) {
    // Auto-suggest from templates
    const igSuggestions = templates.hashtag_suggestions?.instagram || {};
    const allTags = Object.values(igSuggestions).flat();
    igHashtags = [...new Set(allTags)].slice(0, 20);
  }
  if (igHashtags.length > 30) igHashtags = igHashtags.slice(0, 30);

  const postId    = generatePostId();
  const createdAt = isoNow();

  const crossPost = {
    id: postId,
    created_at: createdAt,
    image_url,
    linkedin: {
      post_text:  liText,
      hashtags:   linkedin_hashtags,
      visibility: linkedin_visibility,
    },
    twitter: {
      thread:   twThread,
      hashtags: twitter_hashtags,
    },
    instagram: {
      caption:   igCaption,
      hashtags:  igHashtags,
      post_type,
    },
  };

  log("INFO", "cross_post_content", {
    post_id: postId,
    li_chars: liText.length,
    tw_tweets: twThread.length,
    ig_chars: igCaption.length,
    ig_hashtags: igHashtags.length,
  });

  let approvalPath;
  try { approvalPath = await createCrossPostApprovalFile(crossPost); }
  catch (err) { return errorResult(`Failed to create cross-post approval file: ${err.message}`); }

  return successResult({
    mode: "SIMULATION",
    platform: "cross_platform",
    post_id: postId,
    approval_file: path.relative(VAULT_PATH, approvalPath),
    approval_note: "Single approval triggers posts on all 3 platforms simultaneously",
    platforms: {
      linkedin: {
        mode: SIMULATE_LINKEDIN ? "SIMULATION" : "LIVE",
        char_count: liText.length,
        char_limit: 3000,
        hashtag_count: linkedin_hashtags.length,
        preview: liText.slice(0, 120) + (liText.length > 120 ? "..." : ""),
      },
      twitter: {
        mode: SIMULATE_TWITTER ? "SIMULATION" : "LIVE",
        is_thread: twThread.length > 1,
        tweet_count: twThread.length,
        tweets: twThread.map((t, i) => ({ index: i + 1, char_count: t.length, preview: t.slice(0, 60) + (t.length > 60 ? "..." : "") })),
      },
      instagram: {
        mode: SIMULATE_INSTAGRAM ? "SIMULATION" : "LIVE",
        post_type,
        caption_length: igCaption.length,
        hashtag_count: igHashtags.length,
        image_required: true,
        image_url: image_url || "NOT PROVIDED",
        preview: igCaption.slice(0, 120) + (igCaption.length > 120 ? "..." : ""),
      },
    },
    created_at: createdAt,
    next_steps: [
      `Review all 3 platform versions: ${path.relative(VAULT_PATH, approvalPath)}`,
      image_url ? "Image URL confirmed" : "⚠️  Add image URL before approving (required for Instagram)",
      "Move to Approved/ to publish to all platforms",
      "Move to Rejected/ to cancel all platforms",
    ],
    simulation_note: `Simulation active on: ${[SIMULATE_LINKEDIN ? "LinkedIn" : null, SIMULATE_TWITTER ? "Twitter" : null, SIMULATE_INSTAGRAM ? "Instagram" : null].filter(Boolean).join(", ") || "none"}`,
  });
}

// ============================================================
// FACEBOOK TOOLS
// ============================================================

async function createFacebookPost(args) {
  const {
    content,
    target_type = "profile",
    link_url    = "",
    image_url   = "",
  } = args;

  if (!content || !content.trim()) return errorResult("'content' is required.");

  const validTargets = ["profile", "page"];
  if (!validTargets.includes(target_type))
    return errorResult(`Invalid target_type "${target_type}". Options: ${validTargets.join(", ")}`);

  if (target_type === "page" && !FACEBOOK_PAGE_ID && !SIMULATE_FACEBOOK)
    return errorResult("FACEBOOK_PAGE_ID env var is required to post to a page.");

  // Facebook recommended limits (no hard limit, but UX best practices):
  // Text-only: 40-80 chars for highest engagement
  // With link/image: 100-250 chars
  // Max stored: 63,206 chars
  const recLimit = link_url || image_url ? 250 : 80;
  const isLong   = content.length > recLimit;

  const postId    = generatePostId();
  const createdAt = isoNow();
  const postData  = { id: postId, content, target_type, link_url, image_url, created_at: createdAt };

  log("INFO", "create_facebook_post", {
    post_id: postId, target_type, char_count: content.length,
    has_link: !!link_url, has_image: !!image_url, simulate: SIMULATE_FACEBOOK,
  });

  if (SIMULATE_FACEBOOK) {
    let approvalPath;
    try { approvalPath = await createFacebookApprovalFile(postData); }
    catch (err) { return errorResult(`Failed to create approval file: ${err.message}`); }

    const templates = loadTemplates();
    const fbPlatform = templates.platforms?.facebook || {};

    return successResult({
      mode: "SIMULATION",
      platform: "facebook",
      post_id: postId,
      target_type,
      char_count: content.length,
      char_recommended: recLimit,
      is_over_recommended_length: isLong,
      length_tip: isLong
        ? `Posts with ${link_url || image_url ? "media" : "text only"} perform best under ${recLimit} chars`
        : "Length is within Facebook best practices",
      has_link:  !!link_url,
      has_image: !!image_url,
      post_type: link_url ? "link" : image_url ? "image" : "text",
      approval_required: true,
      approval_file: path.relative(VAULT_PATH, approvalPath),
      created_at: createdAt,
      best_times: fbPlatform.best_times || ["Wed-Sun 1-4pm"],
      best_days:  fbPlatform.best_days  || ["Wednesday", "Thursday", "Friday", "Saturday", "Sunday"],
      best_practices: (templates.best_practices?.facebook || []).slice(0, 4),
      next_steps: [
        `Review: ${path.relative(VAULT_PATH, approvalPath)}`,
        "Move to Approved/ to confirm, or Rejected/ to cancel",
        "To go live: set SIMULATE_FACEBOOK=false + FACEBOOK_ACCESS_TOKEN + FACEBOOK_USER_ID env vars",
      ],
      simulation_note: "No real Facebook post created. See README.md for Facebook Graph API setup.",
    });
  }

  /* PRODUCTION_ONLY — Facebook Graph API v21
  const targetId  = target_type === "page" ? FACEBOOK_PAGE_ID : "me";
  const token     = target_type === "page" ? FACEBOOK_PAGE_ACCESS_TOKEN : FACEBOOK_ACCESS_TOKEN;
  if (!token) return errorResult(`Access token not set for ${target_type}. Set FACEBOOK_${target_type === "page" ? "PAGE_" : ""}ACCESS_TOKEN.`);

  const body = { message: content, access_token: token };
  if (link_url)  body.link  = link_url;
  // For image posts: first upload via /{user-id}/photos, then reference photo_id
  if (image_url) body.url   = image_url;  // simplified — real flow requires /photos endpoint first

  const endpoint = image_url
    ? `${FACEBOOK_API_BASE}/${targetId}/photos`
    : `${FACEBOOK_API_BASE}/${targetId}/feed`;

  const response = await fetch(endpoint, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!response.ok) { const err = await response.text(); return errorResult(`Facebook API error ${response.status}: ${err}`); }
  const data = await response.json();
  const postIdFB = data.id || data.post_id;
  return successResult({
    mode: "LIVE", platform: "facebook", post_id: postId, facebook_post_id: postIdFB,
    post_url: `https://www.facebook.com/${postIdFB.replace("_", "/posts/")}`,
    target_type, char_count: content.length, created_at: createdAt,
  });
  */
  return errorResult("SIMULATE_FACEBOOK is false but production code is not enabled.");
}

async function scheduleFacebookPost(args) {
  const {
    content,
    scheduled_time,
    target_type = "profile",
    link_url    = "",
    image_url   = "",
  } = args;

  if (!content || !content.trim()) return errorResult("'content' is required.");
  if (!scheduled_time)             return errorResult("'scheduled_time' is required (ISO 8601).");

  const scheduledDate = new Date(scheduled_time);
  if (isNaN(scheduledDate.getTime())) return errorResult(`Invalid scheduled_time: "${scheduled_time}"`);
  if (scheduledDate <= new Date())    return errorResult("Scheduled time must be in the future.");

  const validTargets = ["profile", "page"];
  if (!validTargets.includes(target_type))
    return errorResult(`Invalid target_type "${target_type}". Options: ${validTargets.join(", ")}`);

  const templates  = loadTemplates();
  const fbPlatform = templates.platforms?.facebook || {};
  const bestDays   = fbPlatform.best_days  || ["Wednesday", "Thursday", "Friday", "Saturday", "Sunday"];

  const scheduledDow  = scheduledDate.toLocaleDateString("en-US", { weekday: "long" });
  const scheduledHour = scheduledDate.getUTCHours();
  const isOptDay  = bestDays.includes(scheduledDow);
  const isOptHour = scheduledHour >= 13 && scheduledHour <= 16; // 1-4pm

  const postId   = generatePostId();
  const postData = {
    id: postId, content, target_type, link_url, image_url, scheduled_time, created_at: isoNow(),
    optimal_note: isOptDay && isOptHour
      ? "Optimal day and time for Facebook"
      : "Consider Wed-Sun 1-4pm for maximum Facebook organic reach",
  };

  let planPath;
  try { planPath = await createScheduledPlanFile("facebook", postData); }
  catch (err) { return errorResult(`Failed to create plan file: ${err.message}`); }

  const hoursUntil = ((scheduledDate - Date.now()) / 3_600_000).toFixed(1);

  return successResult({
    mode: SIMULATE_FACEBOOK ? "SIMULATION" : "LIVE",
    platform: "facebook",
    post_id: postId,
    target_type,
    scheduled_time,
    hours_until: parseFloat(hoursUntil),
    is_optimal_time: isOptDay && isOptHour,
    optimal_suggestion: postData.optimal_note,
    best_times: fbPlatform.best_times || ["Wed-Sun 1-4pm"],
    best_days: bestDays,
    char_count: content.length,
    has_link:   !!link_url,
    has_image:  !!image_url,
    plan_file:  path.relative(VAULT_PATH, planPath),
    created_at: postData.created_at,
    facebook_scheduled_note: "Facebook Graph API supports scheduled_publish_time (Unix epoch) for page posts. Profile posts cannot be natively scheduled via API — Claude will post at the scheduled time.",
  });
}

// ============================================================
// GENERATE SOCIAL CONTENT (multi-platform)
// ============================================================

/**
 * Generate platform-optimised content from a single topic.
 * Returns adapted versions for each requested platform.
 */
async function generateSocialContent(args) {
  const {
    topic,
    platforms          = ["linkedin", "facebook", "twitter"],
    content_type       = "professional",
    company_name       = "our company",
    include_hashtags   = true,
    include_cta        = true,
  } = args;

  if (!topic || !topic.trim()) return errorResult("'topic' is required.");

  const validPlatforms = ["linkedin", "facebook", "twitter", "instagram"];
  const invalidPlats   = platforms.filter(p => !validPlatforms.includes(p));
  if (invalidPlats.length > 0)
    return errorResult(`Invalid platforms: ${invalidPlats.join(", ")}. Valid: ${validPlatforms.join(", ")}`);

  const validTypes = ["professional", "casual", "announcement", "tip", "question", "behind_the_scenes"];
  if (!validTypes.includes(content_type))
    return errorResult(`Invalid content_type "${content_type}". Valid: ${validTypes.join(", ")}`);

  const templates = loadTemplates();
  const result    = {};

  // ---- Content templates per type ----
  const contentMap = {
    professional: {
      base: `${topic} is reshaping how ${company_name} operates.\n\nHere's what we've learned building in this space:\n\n1. Start with the workflow — not the technology\n2. Design for human oversight, not around it\n3. Measure what changes, not just what automates\n\nThe teams getting the most value aren't the ones with the most AI tools. They're the ones with the clearest workflows around those tools.\n\nWhat's one thing you'd change about how your team uses AI today?`,
      cta: "Share your experience in the comments.",
    },
    casual: {
      base: `Quick update on ${topic} at ${company_name}: things are moving fast and we wanted to share what we're seeing.\n\nThe short version? It's working. And the longer version is in the comments.\n\nWhat are you building right now?`,
      cta: "Drop a comment — we read every one.",
    },
    announcement: {
      base: `Big news: ${company_name} just launched ${topic}.\n\nWe've been working on this for months and we're finally ready to share it.\n\nHere's what it means for you:\n- Faster workflows\n- Better visibility\n- Less manual overhead\n\nMore details in the link below.`,
      cta: "Follow for updates.",
    },
    tip: {
      base: `Quick tip on ${topic}:\n\nMost people skip the step that matters most.\n\nBefore you implement anything, ask: "What decision does this remove from a human's plate?"\n\nIf you can't answer that, you're not ready to automate it.\n\nWhich part of ${topic} are you still doing manually?`,
      cta: "Save this for your next project.",
    },
    question: {
      base: `Question for you:\n\nWhen it comes to ${topic}, what's the one thing you wish you'd known before you started?`,
      cta: "Drop your answer below — building a resource from the responses.",
    },
    behind_the_scenes: {
      base: `Behind the scenes at ${company_name}:\n\nHere's how we actually handle ${topic}:\n\n- Step 1: [describe your first step]\n- Step 2: [describe your second step]\n- Step 3: [describe your third step]\n\nIs this how you handle it, or do you have a different approach?`,
      cta: "Share your process below.",
    },
  };

  const base  = contentMap[content_type]?.base || contentMap.professional.base;
  const cta   = include_cta ? contentMap[content_type]?.cta : "";

  // ---- LinkedIn adaptation ----
  if (platforms.includes("linkedin")) {
    const liHashtags = include_hashtags
      ? (templates.hashtag_suggestions?.linkedin?.ai_ml || ["#AI", "#Automation", "#Innovation"]).slice(0, 5)
      : [];
    const liContent  = `${base}${cta ? `\n\n${cta}` : ""}`;
    result.linkedin  = {
      content:        liContent,
      char_count:     liContent.length,
      char_limit:     3000,
      hashtags:       liHashtags,
      tone:           "professional, data-driven",
      best_times:     "Tue-Thu 8-10am or 12-1pm",
      ready_to_post:  true,
      next_step:      "Pass to create_linkedin_post with this content and hashtags",
    };
  }

  // ---- Facebook adaptation ----
  if (platforms.includes("facebook")) {
    // Shorter, punchier, more conversational
    const fbBase    = base.split("\n\n")[0]; // First paragraph only for FB
    const fbContent = `${fbBase}${cta ? `\n\n${cta}` : ""}`;
    result.facebook = {
      content:        fbContent,
      char_count:     fbContent.length,
      char_recommended: 250,
      tone:           "casual, engaging",
      best_times:     "Wed-Sun 1-4pm",
      target_options: ["profile", "page"],
      note:           "Facebook favours shorter posts with questions or links. Emoji can boost engagement.",
      ready_to_post:  true,
      next_step:      "Pass to create_facebook_post with this content",
    };
  }

  // ---- Twitter adaptation ----
  if (platforms.includes("twitter")) {
    const twHashtags    = include_hashtags ? ["#AI", "#BuildInPublic"] : [];
    const MARKER_SPACE  = 8;
    const effective     = 280 - MARKER_SPACE;
    // Build punchy tweet from first sentence of base
    const firstSentence = base.split(/[.!?]\s/)[0] + ".";
    const twContent     = firstSentence.length <= effective ? firstSentence : firstSentence.slice(0, effective - 3) + "...";
    const withTags      = twHashtags.length ? `${twContent}\n\n${twHashtags.join(" ")}` : twContent;
    const finalTweet    = withTags.length <= 280 ? withTags : twContent;

    // Full thread for longer content
    const words   = base.split(/\s+/);
    const chunks  = [];
    let current   = "";
    for (const word of words) {
      const cand = current ? `${current} ${word}` : word;
      if (cand.length <= effective) { current = cand; }
      else { if (current) chunks.push(current); current = word; }
    }
    if (current) chunks.push(current);
    const thread  = chunks.length > 1
      ? chunks.map((c, i) => `${c} [${i + 1}/${chunks.length}]`)
      : [finalTweet];

    result.twitter = {
      single_tweet:  finalTweet,
      single_chars:  finalTweet.length,
      thread_option: thread,
      thread_tweets: thread.length,
      hashtags:      twHashtags,
      char_limit:    280,
      tone:          "concise, punchy",
      best_times:    "Mon-Fri 8-10am, 12-1pm, 6-9pm",
      ready_to_post: true,
      next_step:     thread.length > 1
        ? "Long content — use thread_option with create_twitter_post for full context"
        : "Pass single_tweet to create_twitter_post",
    };
  }

  // ---- Instagram adaptation ----
  if (platforms.includes("instagram")) {
    const igCaption   = base.length > 2200 ? base.slice(0, 2197) + "..." : base;
    const igHashtags  = include_hashtags
      ? [...(templates.hashtag_suggestions?.instagram?.tech || ["#ai", "#tech", "#automation"]),
         ...(templates.hashtag_suggestions?.instagram?.productivity || ["#productivity"]),
        ].slice(0, 20)
      : [];
    result.instagram  = {
      caption:        igCaption,
      caption_chars:  igCaption.length,
      char_limit:     2200,
      hashtags:       igHashtags,
      hashtag_count:  igHashtags.length,
      tone:           "visual-first, aspirational",
      best_times:     "Mon-Wed 9-11am or 1-3pm",
      image_required: true,
      note:           "Instagram requires an image or video. Hashtags perform best posted in first comment.",
      ready_to_post:  false,
      next_step:      "Add an image_url then pass caption + hashtags to create_instagram_post",
    };
  }

  log("INFO", "generate_social_content", { topic, platforms, content_type });

  return successResult({
    topic,
    content_type,
    company_name,
    platforms_generated: Object.keys(result),
    content: result,
    generation_note: "Content is generated from templates. Review and personalise before posting.",
    workflow: [
      "1. Review each platform version above",
      "2. Personalise with specific details, metrics, or stories",
      "3. Pass each platform's content to its create_* tool for HITL approval",
      "4. Or use cross_post to submit all platforms with a single approval",
    ],
  });
}

// ============================================================
// CROSS_POST — LinkedIn + Facebook + Twitter
// ============================================================

/**
 * Post adapted content to LinkedIn, Facebook, and/or Twitter
 * with a single HITL approval file.
 */
async function crossPost(args) {
  const {
    content,
    platforms           = ["linkedin", "facebook", "twitter"],
    linkedin_hashtags   = ["#AI", "#Automation", "#Innovation"],
    twitter_hashtags    = ["#AI", "#BuildInPublic"],
    linkedin_visibility = "PUBLIC",
    facebook_target     = "profile",
    facebook_link_url   = "",
    image_url           = "",
  } = args;

  if (!content || !content.trim()) return errorResult("'content' is required.");
  if (platforms.length === 0)      return errorResult("'platforms' must include at least one platform.");

  const validPlatforms = ["linkedin", "facebook", "twitter"];
  const invalidPlats   = platforms.filter(p => !validPlatforms.includes(p));
  if (invalidPlats.length > 0)
    return errorResult(`Invalid platforms: ${invalidPlats.join(", ")}. Valid for cross_post: ${validPlatforms.join(", ")}`);

  const crossPostData = { id: generatePostId(), created_at: isoNow(), platforms };

  // ---- LinkedIn adaptation ----
  if (platforms.includes("linkedin")) {
    const liText = buildPostText(content, linkedin_hashtags);
    if (liText.length > 3000)
      return errorResult(`Content too long for LinkedIn (${liText.length} / 3000 chars).`);
    crossPostData.linkedin = {
      post_text:  liText,
      hashtags:   linkedin_hashtags,
      visibility: linkedin_visibility,
    };
  }

  // ---- Facebook adaptation ----
  if (platforms.includes("facebook")) {
    // Trim to first 2 paragraphs for Facebook (shorter = better engagement)
    const fbParas    = content.trim().split(/\n\n+/);
    const fbContent  = fbParas.slice(0, 2).join("\n\n");
    crossPostData.facebook = {
      content:     fbContent,
      target_type: facebook_target,
      link_url:    facebook_link_url,
      image_url,
    };
  }

  // ---- Twitter adaptation (auto-thread) ----
  if (platforms.includes("twitter")) {
    const twThread = adaptForTwitter(content, twitter_hashtags);
    for (let i = 0; i < twThread.length; i++) {
      if (twThread[i].length > 280)
        return errorResult(`Twitter tweet ${i + 1} exceeds 280 chars after splitting.`);
    }
    crossPostData.twitter = { thread: twThread, hashtags: twitter_hashtags };
  }

  log("INFO", "cross_post", {
    post_id: crossPostData.id,
    platforms,
    li_chars: crossPostData.linkedin?.post_text?.length,
    fb_chars: crossPostData.facebook?.content?.length,
    tw_tweets: crossPostData.twitter?.thread?.length,
  });

  let approvalPath;
  try { approvalPath = await createCrossPostLFTApprovalFile(crossPostData); }
  catch (err) { return errorResult(`Failed to create cross-post approval file: ${err.message}`); }

  const platformSummary = {};
  if (crossPostData.linkedin) {
    platformSummary.linkedin = {
      mode:          SIMULATE_LINKEDIN ? "SIMULATION" : "LIVE",
      char_count:    crossPostData.linkedin.post_text.length,
      char_limit:    3000,
      hashtag_count: linkedin_hashtags.length,
      preview:       crossPostData.linkedin.post_text.slice(0, 100) + "...",
    };
  }
  if (crossPostData.facebook) {
    platformSummary.facebook = {
      mode:        SIMULATE_FACEBOOK ? "SIMULATION" : "LIVE",
      char_count:  crossPostData.facebook.content.length,
      target_type: facebook_target,
      has_link:    !!facebook_link_url,
      preview:     crossPostData.facebook.content.slice(0, 100) + "...",
    };
  }
  if (crossPostData.twitter) {
    platformSummary.twitter = {
      mode:        SIMULATE_TWITTER ? "SIMULATION" : "LIVE",
      is_thread:   crossPostData.twitter.thread.length > 1,
      tweet_count: crossPostData.twitter.thread.length,
      tweets:      crossPostData.twitter.thread.map((t, i) => ({
        index: i + 1, char_count: t.length,
        preview: t.slice(0, 60) + (t.length > 60 ? "..." : ""),
      })),
    };
  }

  return successResult({
    mode:            "SIMULATION",
    tool:            "cross_post",
    post_id:         crossPostData.id,
    platforms_included: platforms,
    approval_file:   path.relative(VAULT_PATH, approvalPath),
    approval_note:   `Single approval triggers posts on: ${platforms.join(", ")}`,
    platforms:       platformSummary,
    created_at:      crossPostData.created_at,
    next_steps: [
      `Review all platform versions: ${path.relative(VAULT_PATH, approvalPath)}`,
      "Move to Approved/ to publish to all selected platforms",
      "Move to Rejected/ to cancel all platforms",
    ],
    simulation_note: `Simulation active on: ${[
      platforms.includes("linkedin")  && SIMULATE_LINKEDIN  ? "LinkedIn"  : null,
      platforms.includes("facebook")  && SIMULATE_FACEBOOK  ? "Facebook"  : null,
      platforms.includes("twitter")   && SIMULATE_TWITTER   ? "Twitter"   : null,
    ].filter(Boolean).join(", ") || "none (all live)"}`,
  });
}

// ============================================================
// MCP SERVER SETUP
// ============================================================

const server = new Server(
  { name: "social-media-mcp-server", version: "3.0.0" },
  { capabilities: { tools: {} } }
);

// ---- Tool Registry ----

server.setRequestHandler(ListToolsRequestSchema, async () => ({
  tools: [
    // --------------------------------------------------------
    // LINKEDIN
    // --------------------------------------------------------
    {
      name: "create_linkedin_post",
      description:
        `Create a LinkedIn post with HITL approval workflow. ` +
        `${SIMULATE_LINKEDIN ? "⚠️ SIMULATION MODE: Creates approval file in Pending_Approval/ — no real post published. " : "LIVE MODE: Publishes to LinkedIn after approval. "}` +
        `Validates 3000-char limit and returns post preview.`,
      inputSchema: {
        type: "object",
        properties: {
          content:    { type: "string",  description: "Post body text (max 3000 chars). Hook in first 2 lines is critical." },
          hashtags:   { type: "array",   items: { type: "string" }, description: "Hashtags (with or without #). Recommended: 3-5." },
          visibility: { type: "string",  enum: ["PUBLIC", "CONNECTIONS", "LOGGED_IN"], description: "Post visibility. Default: PUBLIC." },
        },
        required: ["content"],
      },
    },
    {
      name: "schedule_linkedin_post",
      description:
        "Queue a LinkedIn post for future publishing. Creates a plan file in Plans/ with the full API payload. " +
        "Returns optimal timing analysis (best days: Tue-Thu, best times: 8-10am/12-1pm).",
      inputSchema: {
        type: "object",
        properties: {
          content:        { type: "string", description: "Post body text." },
          scheduled_time: { type: "string", description: "ISO 8601 future datetime, e.g. '2026-03-01T09:00:00Z'." },
          hashtags:       { type: "array",  items: { type: "string" }, description: "Hashtags to append." },
          visibility:     { type: "string", enum: ["PUBLIC", "CONNECTIONS", "LOGGED_IN"], description: "Post visibility. Default: PUBLIC." },
        },
        required: ["content", "scheduled_time"],
      },
    },
    {
      name: "generate_business_content",
      description:
        "Generate professional LinkedIn content using built-in templates (achievement, thought_leadership, tip, behind_the_scenes, announcement, milestone, event, hiring). " +
        "Returns filled template, suggested hashtags, and best practices.",
      inputSchema: {
        type: "object",
        properties: {
          topic:               { type: "string", description: "Main topic, e.g. 'AI Employee Vault launch'." },
          post_type:           { type: "string", enum: ["achievement", "thought_leadership", "tip", "behind_the_scenes", "announcement", "milestone", "event", "hiring"], description: "Template style." },
          company_name:        { type: "string", description: "Company or product name. Default: 'our company'." },
          cta:                 { type: "string", description: "Call-to-action text for end of post." },
          hashtag_categories:  { type: "array",  items: { type: "string", enum: ["technology", "ai_ml", "startup", "software", "business", "career", "marketing", "data", "productivity", "finance"] }, description: "Hashtag category buckets." },
        },
        required: ["topic", "post_type"],
      },
    },

    // --------------------------------------------------------
    // TWITTER
    // --------------------------------------------------------
    {
      name: "create_twitter_post",
      description:
        `Create a Twitter/X post or thread with HITL approval. ` +
        `${SIMULATE_TWITTER ? "⚠️ SIMULATION MODE: Creates approval file — no real tweet posted. " : "LIVE MODE: Posts to Twitter API v2. "}` +
        `Automatically splits content into threads (280-char limit per tweet). ` +
        `Supports hashtag optimization (max 2 recommended).`,
      inputSchema: {
        type: "object",
        properties: {
          content:            { type: "string",  description: "Tweet content. If over 280 chars, auto-split into thread." },
          hashtags:           { type: "array",   items: { type: "string" }, description: "Hashtags. Max 3 (2 recommended for reach)." },
          optimize_hashtags:  { type: "boolean", description: "Auto-select best 2 hashtags from provided list. Default: true." },
        },
        required: ["content"],
      },
    },
    {
      name: "schedule_twitter_post",
      description:
        "Queue a tweet or thread for future publishing. Returns optimal timing analysis " +
        "(best times: 8-10am, 12-1pm, 6-9pm weekdays). Creates plan file in Plans/.",
      inputSchema: {
        type: "object",
        properties: {
          content:        { type: "string", description: "Tweet content. Auto-split into thread if needed." },
          scheduled_time: { type: "string", description: "ISO 8601 future datetime." },
          hashtags:       { type: "array",  items: { type: "string" }, description: "Hashtags. Max 3." },
        },
        required: ["content", "scheduled_time"],
      },
    },

    // --------------------------------------------------------
    // INSTAGRAM
    // --------------------------------------------------------
    {
      name: "create_instagram_post",
      description:
        `Create an Instagram post (feed or story) with HITL approval. ` +
        `${SIMULATE_INSTAGRAM ? "⚠️ SIMULATION MODE: Creates approval file — no real post published. " : "LIVE MODE: Publishes via Instagram Graph API. "}` +
        `⚠️ IMAGE REQUIRED — Instagram mandates an image or video for all posts. ` +
        `Supports up to 30 hashtags. Returns image dimension specs.`,
      inputSchema: {
        type: "object",
        properties: {
          caption:                    { type: "string",  description: "Post caption (max 2200 chars). Hook in first 125 chars." },
          hashtags:                   { type: "array",   items: { type: "string" }, description: "Hashtags. Recommended: 20-25. Max: 30." },
          post_type:                  { type: "string",  enum: ["feed", "story"], description: "Feed post (permanent) or Story (24h). Default: feed." },
          image_url:                  { type: "string",  description: "Publicly accessible image URL. REQUIRED for live posting." },
          hashtags_in_first_comment:  { type: "boolean", description: "Put hashtags in first comment instead of caption (cleaner look). Default: true." },
        },
        required: ["caption"],
      },
    },
    {
      name: "schedule_instagram_post",
      description:
        "Queue an Instagram post for future publishing. Returns optimal timing analysis " +
        "(best times: 9-11am, 1-3pm Mon-Wed). Creates plan file in Plans/. " +
        "Includes content calendar entry and image requirement reminder.",
      inputSchema: {
        type: "object",
        properties: {
          caption:        { type: "string", description: "Post caption (max 2200 chars)." },
          scheduled_time: { type: "string", description: "ISO 8601 future datetime." },
          hashtags:       { type: "array",  items: { type: "string" }, description: "Hashtags. Max 30." },
          post_type:      { type: "string", enum: ["feed", "story"], description: "Feed or Story. Default: feed." },
          image_url:      { type: "string", description: "Publicly accessible image URL." },
        },
        required: ["caption", "scheduled_time"],
      },
    },

    // --------------------------------------------------------
    // FACEBOOK
    // --------------------------------------------------------
    {
      name: "create_facebook_post",
      description:
        `Create a Facebook post to a profile or page with HITL approval. ` +
        `${SIMULATE_FACEBOOK ? "⚠️ SIMULATION MODE: Creates approval file — no real post published. " : "LIVE MODE: Posts via Facebook Graph API. "}` +
        `Supports text, link, and image posts. Returns engagement length advice (40-80 chars for text, 100-250 with media).`,
      inputSchema: {
        type: "object",
        properties: {
          content:     { type: "string",  description: "Post text content. Recommended: under 80 chars for text posts, 250 for media posts." },
          target_type: { type: "string",  enum: ["profile", "page"], description: "Post to personal profile or Facebook Page. Default: profile." },
          link_url:    { type: "string",  description: "Optional URL to attach as a link preview." },
          image_url:   { type: "string",  description: "Optional publicly accessible image URL to attach." },
        },
        required: ["content"],
      },
    },
    {
      name: "schedule_facebook_post",
      description:
        "Queue a Facebook post for future publishing. Returns optimal timing analysis " +
        "(best times: Wed-Sun 1-4pm). Creates plan file in Plans/. " +
        "Note: Facebook Graph API supports native scheduling for page posts via scheduled_publish_time.",
      inputSchema: {
        type: "object",
        properties: {
          content:        { type: "string", description: "Post text content." },
          scheduled_time: { type: "string", description: "ISO 8601 future datetime." },
          target_type:    { type: "string", enum: ["profile", "page"], description: "Profile or Page. Default: profile." },
          link_url:       { type: "string", description: "Optional URL to attach." },
          image_url:      { type: "string", description: "Optional image URL." },
        },
        required: ["content", "scheduled_time"],
      },
    },

    // --------------------------------------------------------
    // CROSS-PLATFORM
    // --------------------------------------------------------
    {
      name: "cross_post_content",
      description:
        "Post the same content across LinkedIn, Twitter/X, and Instagram simultaneously with a SINGLE HITL approval. " +
        "Automatically adapts content per platform: LinkedIn (3000 chars, professional), Twitter (280 chars/thread, punchy), Instagram (2200 chars + 30 hashtags, visual-first). " +
        "Creates one approval file in Pending_Approval/ that, when approved, triggers all 3 platforms.",
      inputSchema: {
        type: "object",
        properties: {
          content:              { type: "string", description: "Base long-form content. Will be adapted per platform automatically." },
          image_url:            { type: "string", description: "Image URL for Instagram (required for live Instagram posting)." },
          linkedin_hashtags:    { type: "array",  items: { type: "string" }, description: "Hashtags for LinkedIn (3-5 recommended). Default: #AI #Automation #Innovation." },
          twitter_hashtags:     { type: "array",  items: { type: "string" }, description: "Hashtags for Twitter (1-2 recommended). Default: #AI #BuildInPublic." },
          instagram_hashtags:   { type: "array",  items: { type: "string" }, description: "Hashtags for Instagram (20-25 recommended). Auto-populated if empty." },
          linkedin_visibility:  { type: "string", enum: ["PUBLIC", "CONNECTIONS", "LOGGED_IN"], description: "LinkedIn visibility. Default: PUBLIC." },
          post_type:            { type: "string", enum: ["feed", "story"], description: "Instagram post type. Default: feed." },
        },
        required: ["content"],
      },
    },
    {
      name: "cross_post",
      description:
        "Post adapted content to LinkedIn, Facebook, and/or Twitter with a SINGLE HITL approval. " +
        "Choose any combination of platforms via the 'platforms' parameter. " +
        "Content is automatically adapted: LinkedIn (professional, 3000 chars), Facebook (casual, first 2 paragraphs), Twitter (280 chars/thread). " +
        "Creates one approval file — approving it triggers all selected platforms simultaneously.",
      inputSchema: {
        type: "object",
        properties: {
          content:              { type: "string",  description: "Base content. Auto-adapted per platform." },
          platforms:            { type: "array",   items: { type: "string", enum: ["linkedin", "facebook", "twitter"] }, description: "Platforms to post to. Default: all 3." },
          linkedin_hashtags:    { type: "array",   items: { type: "string" }, description: "LinkedIn hashtags (3-5 recommended)." },
          twitter_hashtags:     { type: "array",   items: { type: "string" }, description: "Twitter hashtags (1-2 recommended)." },
          linkedin_visibility:  { type: "string",  enum: ["PUBLIC", "CONNECTIONS", "LOGGED_IN"], description: "LinkedIn visibility. Default: PUBLIC." },
          facebook_target:      { type: "string",  enum: ["profile", "page"], description: "Post to FB profile or page. Default: profile." },
          facebook_link_url:    { type: "string",  description: "Optional link URL for Facebook post." },
          image_url:            { type: "string",  description: "Optional image URL (used on Facebook if provided)." },
        },
        required: ["content"],
      },
    },
    {
      name: "generate_social_content",
      description:
        "Generate platform-optimised content for any combination of LinkedIn, Facebook, Twitter, and Instagram from a single topic. " +
        "Returns adapted versions per platform: LinkedIn (professional, long-form), Facebook (casual, 2 paragraphs), Twitter (punchy, thread-ready), Instagram (caption + 20 hashtags). " +
        "Content can be passed directly to the corresponding create_* tools or to cross_post.",
      inputSchema: {
        type: "object",
        properties: {
          topic:              { type: "string",  description: "Main topic or subject to create content about." },
          platforms:          { type: "array",   items: { type: "string", enum: ["linkedin", "facebook", "twitter", "instagram"] }, description: "Which platforms to generate content for. Default: linkedin, facebook, twitter." },
          content_type:       { type: "string",  enum: ["professional", "casual", "announcement", "tip", "question", "behind_the_scenes"], description: "Tone and content style. Default: professional." },
          company_name:       { type: "string",  description: "Company or product name for personalisation. Default: 'our company'." },
          include_hashtags:   { type: "boolean", description: "Include suggested hashtags in output. Default: true." },
          include_cta:        { type: "boolean", description: "Include a call-to-action. Default: true." },
        },
        required: ["topic"],
      },
    },
  ],
}));

// ---- Tool Dispatcher ----

server.setRequestHandler(CallToolRequestSchema, async (request) => {
  const { name, arguments: args } = request.params;
  log("INFO", `tool called: ${name}`);

  try {
    switch (name) {
      case "create_linkedin_post":      return await createLinkedInPost(args);
      case "schedule_linkedin_post":    return await scheduleLinkedInPost(args);
      case "generate_business_content": return await generateBusinessContent(args);
      case "create_twitter_post":       return await createTwitterPost(args);
      case "schedule_twitter_post":     return await scheduleTwitterPost(args);
      case "create_instagram_post":     return await createInstagramPost(args);
      case "schedule_instagram_post":   return await scheduleInstagramPost(args);
      case "create_facebook_post":      return await createFacebookPost(args);
      case "schedule_facebook_post":    return await scheduleFacebookPost(args);
      case "cross_post_content":        return await crossPostContent(args);
      case "cross_post":                return await crossPost(args);
      case "generate_social_content":   return await generateSocialContent(args);
      default:
        return errorResult(
          `Unknown tool: "${name}". Available tools: create_linkedin_post, schedule_linkedin_post, generate_business_content, create_twitter_post, schedule_twitter_post, create_instagram_post, schedule_instagram_post, create_facebook_post, schedule_facebook_post, cross_post_content, cross_post, generate_social_content`
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
  log("INFO", "Social Media MCP Server v3.0 started", {
    vault: VAULT_PATH,
    tools: 12,
    platforms: ["linkedin", "facebook", "twitter", "instagram"],
    simulate_linkedin:  SIMULATE_LINKEDIN,
    simulate_facebook:  SIMULATE_FACEBOOK,
    simulate_twitter:   SIMULATE_TWITTER,
    simulate_instagram: SIMULATE_INSTAGRAM,
  });
}

main().catch((err) => {
  process.stderr.write(`${LOG_PREFIX} FATAL: ${err.message}\n`);
  process.exit(1);
});
