# Social Media MCP Server v3.0

Unified Gold Tier MCP server for LinkedIn, Facebook, Twitter/X, and Instagram.
Part of the **AI Employee Vault** hackathon project.

---

## Overview

This server provides **12 tools** across 4 platforms in a single MCP server,
all with HITL (Human-in-the-Loop) approval and simulation mode.

| Tool | Platform | Purpose |
|------|----------|---------|
| `create_linkedin_post` | LinkedIn | Draft post → approval file |
| `schedule_linkedin_post` | LinkedIn | Queue for future publish |
| `generate_business_content` | LinkedIn | LinkedIn template-based content gen |
| `create_twitter_post` | Twitter/X | Draft tweet/thread → approval |
| `schedule_twitter_post` | Twitter/X | Queue for future publish |
| `create_instagram_post` | Instagram | Draft caption+image → approval |
| `schedule_instagram_post` | Instagram | Queue for future publish |
| `create_facebook_post` | Facebook | Post to profile or page → approval |
| `schedule_facebook_post` | Facebook | Queue for future publish |
| `cross_post_content` | LI + TW + IG | Single approval → 3 platforms |
| `cross_post` | LI + FB + TW | Single approval → choose platforms |
| `generate_social_content` | All 4 | Multi-platform content generation |

---

## Quick Start

```bash
cd mcp_servers/social_media_mcp
npm install
node index.js    # Test — should start and wait for JSON-RPC input
```

All platforms default to **SIMULATION MODE** — no real API calls until credentials are configured.

---

## Simulation Mode

Each platform has an independent simulation flag at the top of `index.js`:

```javascript
const SIMULATE_LINKEDIN  = true;   // flip to false + set LINKEDIN_ACCESS_TOKEN
const SIMULATE_FACEBOOK  = true;   // flip to false + set FACEBOOK_ACCESS_TOKEN + FACEBOOK_USER_ID
const SIMULATE_TWITTER   = true;   // flip to false + set TWITTER_* env vars
const SIMULATE_INSTAGRAM = true;   // flip to false + set INSTAGRAM_* env vars
```

In simulation mode, the server:
- Creates HITL approval files in `Pending_Approval/`
- Creates scheduled plan files in `Plans/`
- Returns full post previews with per-platform formatting
- Logs all simulated actions to stderr

---

## Platform Setup

### LinkedIn API

**Requirements:** LinkedIn Marketing Developer Platform approval for `w_member_social` scope.

#### Step 1 — Create LinkedIn App

1. Go to [LinkedIn Developer Portal](https://www.linkedin.com/developers/apps)
2. Click **Create App**
3. Fill in: App Name, LinkedIn Page, Privacy Policy URL, App Logo
4. Under **Products**, request **Share on LinkedIn** (grants `w_member_social`)

#### Step 2 — Get Authorization Code (OAuth 2.0 Authorization Code Flow)

```
GET https://www.linkedin.com/oauth/v2/authorization
  ?response_type=code
  &client_id={CLIENT_ID}
  &redirect_uri={YOUR_REDIRECT_URI}
  &scope=w_member_social%20r_liteprofile
  &state={RANDOM_STATE_STRING}
```

Redirect the user to this URL. After they approve, LinkedIn redirects to your URI with `?code=...`.

#### Step 3 — Exchange Code for Access Token

```bash
curl -X POST https://www.linkedin.com/oauth/v2/accessToken \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "grant_type=authorization_code" \
  -d "code={AUTHORIZATION_CODE}" \
  -d "redirect_uri={YOUR_REDIRECT_URI}" \
  -d "client_id={CLIENT_ID}" \
  -d "client_secret={CLIENT_SECRET}"
```

Response: `{ "access_token": "...", "expires_in": 5183999, ... }`

#### Step 4 — Get Your Person URN

```bash
curl -H "Authorization: Bearer {ACCESS_TOKEN}" \
     -H "X-Restli-Protocol-Version: 2.0.0" \
     https://api.linkedin.com/v2/me
```

Response includes `"id"` — build URN as `urn:li:person:{id}`.

#### Step 5 — Set Environment Variables

```bash
set LINKEDIN_ACCESS_TOKEN=your_access_token
set LINKEDIN_PERSON_URN=urn:li:person:your_id
```

#### LinkedIn API Reference

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/v2/ugcPosts` | POST | Create a post |
| `/v2/me` | GET | Get profile/URN |
| `/v2/shares` | POST | Legacy share endpoint |

- **Rate limits:** 3 posts/day per member, 150 API calls/day (Basic), 500/day (Marketing)
- **Token expiry:** 60 days; use refresh token to renew
- **Scopes needed:** `w_member_social` (post), `r_liteprofile` (profile)

---

### Facebook Graph API

**Requirements:** Facebook Developer account. Personal profile uses User Access Token; pages require Page Access Token.

#### Step 1 — Create Facebook App

1. Go to [Meta for Developers](https://developers.facebook.com/)
2. Click **Create App** → Select **Business** type
3. Add these products to your app:
   - **Facebook Login** (for user token flow)
   - **Pages API** (if posting to a Page)

#### Step 2 — Get User Access Token

**For production**, implement the OAuth 2.0 Authorization Code flow:

```
Redirect user to:
https://www.facebook.com/v21.0/dialog/oauth
  ?client_id={APP_ID}
  &redirect_uri={REDIRECT_URI}
  &scope=publish_actions,pages_manage_posts,pages_read_engagement

Exchange code for token:
GET https://graph.facebook.com/v21.0/oauth/access_token
  ?client_id={APP_ID}&redirect_uri={REDIRECT_URI}
  &client_secret={APP_SECRET}&code={CODE}
```

#### Step 3 — Exchange for Long-Lived Token (60 days)

```bash
curl "https://graph.facebook.com/v21.0/oauth/access_token
  ?grant_type=fb_exchange_token&client_id={APP_ID}
  &client_secret={APP_SECRET}&fb_exchange_token={SHORT_TOKEN}"
```

#### Step 4 — Get Your User ID + Page Token

```bash
# Get user ID
curl "https://graph.facebook.com/v21.0/me?access_token={TOKEN}"

# Get page tokens (for page posting)
curl "https://graph.facebook.com/v21.0/me/accounts?access_token={TOKEN}"
```

#### Step 5 — Set Environment Variables

```bash
set FACEBOOK_ACCESS_TOKEN=your_long_lived_user_token
set FACEBOOK_USER_ID=your_numeric_user_id
set FACEBOOK_PAGE_ID=your_page_id                         # for page posting
set FACEBOOK_PAGE_ACCESS_TOKEN=your_page_access_token     # for page posting
```

#### Facebook Graph API Reference

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/{user-id}/feed` | POST | Post to personal profile |
| `/{page-id}/feed` | POST | Post to a Facebook Page |
| `/{user-id}/photos` | POST | Upload photo |
| `/me/accounts` | GET | List pages + page tokens |
| `/{post-id}` | DELETE | Delete a post |

**Scheduled page posts** — set `published: false` + `scheduled_publish_time` (Unix epoch).

| Permission | Required for |
|---|---|
| `publish_actions` | Personal timeline posts |
| `pages_manage_posts` | Page posts |
| `pages_read_engagement` | Page insights |

**Token expiry:** Short-lived = 1-2h; Long-lived = 60 days; Page token = never (from long-lived user token).

---

### Twitter / X API v2

**Requirements:** Twitter Developer account + Elevated access for v2 write endpoints.

#### Step 1 — Create Twitter App

1. Go to [Twitter Developer Portal](https://developer.twitter.com/en/portal/dashboard)
2. Create a Project → Create an App
3. Under **User authentication settings**:
   - App permissions: **Read and Write**
   - Type of App: **Web App, Automated App or Bot**
   - Callback URL: `https://your-domain.com/callback` (or `http://localhost:3000/callback`)
4. Save your **API Key**, **API Secret**

#### Step 2 — Generate Access Tokens (OAuth 1.0a)

For user-context posting (posting as yourself), use OAuth 1.0a:

1. In Developer Portal → your App → **Keys and Tokens**
2. Under **Authentication Tokens**, generate **Access Token & Secret**
3. The access token corresponds to your Twitter account

For posting as other users, implement the OAuth 1.0a flow:

```
Step 1: POST https://api.twitter.com/oauth/request_token
Step 2: Redirect user to https://api.twitter.com/oauth/authorize?oauth_token={token}
Step 3: POST https://api.twitter.com/oauth/access_token (with oauth_verifier)
```

#### Step 3 — Set Environment Variables

```bash
set TWITTER_API_KEY=your_api_key
set TWITTER_API_SECRET=your_api_secret
set TWITTER_ACCESS_TOKEN=your_access_token
set TWITTER_ACCESS_SECRET=your_access_token_secret
set TWITTER_BEARER_TOKEN=your_bearer_token
```

#### Step 4 — Test the Connection

```bash
curl -H "Authorization: Bearer {BEARER_TOKEN}" \
     "https://api.twitter.com/2/users/me"
```

#### Twitter API v2 Reference

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/2/tweets` | POST | Create a tweet |
| `/2/users/me` | GET | Get authenticated user info |
| `/2/tweets/{id}` | DELETE | Delete a tweet |

**Thread posting:** Post tweet 1, get `id`, post tweet 2 with `reply: { in_reply_to_tweet_id: id }`.

| Access Level | Monthly Tweet Cap | Notes |
|---|---|---|
| Free | 1,500 | Limited — read-mostly |
| Basic ($100/mo) | 3,000 | Recommended for posting |
| Pro ($5,000/mo) | 1,000,000 | Full access |

**Auth signing:** OAuth 1.0a requires HMAC-SHA1 signing. Use `twitter-api-v2` npm package
(add to package.json dependencies) which handles signing automatically.

---

### Instagram Graph API

**Requirements:** Facebook Developer account + Instagram Business/Creator account linked to a Facebook Page.

#### Step 1 — Prerequisites

1. Instagram account must be a **Business** or **Creator** account (not Personal)
2. Link it to a **Facebook Page** you manage
3. Go to [Meta for Developers](https://developers.facebook.com/)
4. Create an App → Select **Business** type

#### Step 2 — Get Instagram Business Account ID

```bash
# Get your Facebook User ID and Page ID
curl "https://graph.facebook.com/v21.0/me/accounts?access_token={USER_ACCESS_TOKEN}"

# Get Instagram Business Account ID linked to a Page
curl "https://graph.facebook.com/v21.0/{PAGE_ID}?fields=instagram_business_account&access_token={USER_ACCESS_TOKEN}"
# Response: { "instagram_business_account": { "id": "INSTAGRAM_BUSINESS_ID" } }
```

#### Step 3 — Generate Long-Lived Access Token

```bash
# Exchange short-lived token for long-lived (60 days)
curl "https://graph.facebook.com/v21.0/oauth/access_token
  ?grant_type=fb_exchange_token
  &client_id={APP_ID}
  &client_secret={APP_SECRET}
  &fb_exchange_token={SHORT_LIVED_TOKEN}"
```

#### Step 4 — Set Environment Variables

```bash
set INSTAGRAM_ACCESS_TOKEN=your_long_lived_token
set INSTAGRAM_BUSINESS_ID=your_instagram_business_account_id
```

#### Step 5 — Publish a Post (2-Step Process)

```bash
# Step 1: Create media container (image must be publicly accessible URL)
curl -X POST "https://graph.facebook.com/v21.0/{IG_BUSINESS_ID}/media" \
  -F "image_url=https://your-server.com/image.jpg" \
  -F "caption=Your caption here" \
  -F "access_token={ACCESS_TOKEN}"
# Response: { "id": "CONTAINER_ID" }

# Step 2: Publish the container
curl -X POST "https://graph.facebook.com/v21.0/{IG_BUSINESS_ID}/media_publish" \
  -F "creation_id=CONTAINER_ID" \
  -F "access_token={ACCESS_TOKEN}"
# Response: { "id": "MEDIA_ID" }
```

#### Instagram Graph API Reference

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/{ig_id}/media` | POST | Create media container |
| `/{ig_id}/media_publish` | POST | Publish container |
| `/{ig_id}/media` | GET | List published media |
| `/{media_id}/comments` | POST | Add first comment (for hashtags) |

| Limit | Value |
|---|---|
| Posts per day | 50 |
| Caption length | 2,200 chars |
| Hashtags | 30 max |
| Images per carousel | 10 |

**Image requirements (feed):** 1080x1080px (1:1), 1080x1350px (4:5 portrait), or 1080x566px (1.91:1 landscape)
**Story requirements:** 1080x1920px (9:16 vertical)
**Formats:** JPG, PNG (image); MP4, MOV (video)

---

## Platform Content Guidelines

### Facebook

- **Text limit:** 63,206 chars (use under 80 for text posts, 250 with media)
- **Hashtags:** 3 max (Facebook hashtags have minimal discovery impact)
- **Best times:** Wed–Sun 1–4pm
- **Media:** Photos get 2.3x more reach; native video 3x over YouTube links
- **Tone:** Casual, conversational, engaging; emoji welcome
- **Links:** Put URLs in first comment — Facebook's algorithm penalises link posts
- **Pro tip:** End with a direct question — doubles comment rate

### LinkedIn

- **Limit:** 3,000 chars hard, 1,300 recommended
- **Hashtags:** 3–5 recommended
- **Best times:** Tue–Thu 8–10am, 12–1pm
- **Hook:** First 2 lines before "See more" click
- **Tone:** Professional, data-driven, insightful

### Twitter / X

- **Limit:** 280 chars per tweet
- **Threads:** Auto-split long content with `[1/N]` markers
- **Hashtags:** 1–2 max (3+ hurts reach)
- **Best times:** Weekdays 8–10am, 12–1pm, 6–9pm
- **Tone:** Punchy, conversational, bold takes

### Instagram

- **Caption limit:** 2,200 chars
- **Hashtags:** 20–25 in first comment (not caption)
- **Best times:** Mon–Wed 9–11am, 1–3pm
- **Image:** REQUIRED — 1080x1080px or 1080x1350px
- **Tone:** Visual-first, authentic, aspirational

---

## HITL Approval Workflow

1. Call any `create_*` tool → generates `Pending_Approval/PLATFORM_POST_{id}.md`
2. Review the approval file (shows exact post preview per platform)
3. Move to `Approved/` → Claude executes the post (or logs simulation)
4. Move to `Rejected/` → Claude archives without posting
5. Executed posts move to `Done/`

`cross_post_content` creates a single approval file showing all 3 platform versions.
One approval publishes to all platforms.

---

## Files in This Directory

| File | Purpose |
|------|---------|
| `index.js` | Main MCP server — 12 tools, 4 platforms |
| `package.json` | Node.js config (`social-media-mcp-server` v3.0) |
| `social_media_templates.json` | Content templates + hashtag library for all 4 platforms |
| `README.md` | This file — full setup guide for all 4 platform APIs |

---

*Social Media MCP Server v3.0 — AI Employee Vault Gold Tier*
