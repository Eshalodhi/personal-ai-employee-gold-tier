# LinkedIn MCP Server

**AI Employee Vault — Gold Tier**

MCP server for LinkedIn content management with HITL approval workflow.

> ⚠️ **Currently running in SIMULATION MODE** (`SIMULATION_MODE = true` in `index.js`)
>
> LinkedIn's Marketing Developer Platform requires company verification before granting
> `w_member_social` posting access. Until your app is approved, this server:
> - Creates approval request files in `Pending_Approval/`
> - Logs exactly what WOULD be posted
> - Saves scheduled posts as plan files in `Plans/`
>
> The full production code is implemented and documented below.

---

## Tools

### 1. `create_linkedin_post`
Create (or draft) a LinkedIn post with HITL approval.

| Parameter | Type | Required | Description |
|---|---|---|---|
| `content` | string | Yes | Post body (max 3000 chars) |
| `hashtags` | string[] | No | Hashtags (with or without `#`) |
| `visibility` | string | No | `PUBLIC`, `CONNECTIONS`, or `LOGGED_IN` (default: `PUBLIC`) |

**Returns:**
- `post_id` — unique ID for tracking
- `approval_file` — path to `Pending_Approval/LINKEDIN_POST_*.md`
- `post_preview` — exact text as it will appear on LinkedIn

**Simulation behaviour:** Creates `Pending_Approval/LINKEDIN_POST_{id}_{date}.md`.
Move the file to `Approved/` to confirm, `Rejected/` to cancel.

---

### 2. `schedule_linkedin_post`
Queue a post for future publishing.

| Parameter | Type | Required | Description |
|---|---|---|---|
| `content` | string | Yes | Post body |
| `scheduled_time` | string | Yes | ISO 8601 future datetime, e.g. `2026-03-01T09:00:00Z` |
| `hashtags` | string[] | No | Hashtags |
| `visibility` | string | No | `PUBLIC`, `CONNECTIONS`, `LOGGED_IN` |

**Returns:**
- `plan_file` — path to `Plans/LINKEDIN_SCHEDULED_{id}_{date}.md`
- `hours_until_scheduled` — countdown
- Full LinkedIn API payload for reference

---

### 3. `generate_business_content`
Generate professional posts from built-in templates.

| Parameter | Type | Required | Description |
|---|---|---|---|
| `topic` | string | Yes | Subject of the post |
| `post_type` | string | Yes | `announcement`, `thought_leadership`, `milestone`, `tip`, `event`, `hiring` |
| `company_name` | string | No | Company/product name |
| `cta` | string | No | Call-to-action text |
| `hashtag_categories` | string[] | No | `technology`, `ai_ml`, `startup`, `software`, `business`, `career`, `marketing`, `data`, `productivity`, `finance` |

**Returns:** Generated content, suggested hashtags, best practices, character count.

---

## Setup

```bash
cd mcp_servers/linkedin_mcp
npm install
```

No additional setup required for simulation mode.

---

## Going Live: LinkedIn API Setup

### Step 1 — Create a LinkedIn App

1. Go to [LinkedIn Developer Portal](https://www.linkedin.com/developers/apps)
2. Click **Create App**
3. Fill in: App Name, LinkedIn Page, Privacy Policy URL, App Logo
4. Under **Products**, request:
   - **Share on LinkedIn** → grants `w_member_social` scope
   - **Sign In with LinkedIn** → grants `r_liteprofile`, `r_emailaddress`
5. Submit for review (Marketing Developer Platform apps require company verification)

### Step 2 — OAuth 2.0 Authorization

Once approved, implement the Authorization Code flow:

#### 2a. Get Authorization Code

Direct the user to this URL in a browser:

```
https://www.linkedin.com/oauth/v2/authorization
  ?response_type=code
  &client_id=YOUR_CLIENT_ID
  &redirect_uri=YOUR_REDIRECT_URI
  &scope=w_member_social%20r_liteprofile%20r_emailaddress
  &state=RANDOM_CSRF_TOKEN
```

User logs in and approves → LinkedIn redirects to your URI with `?code=AUTH_CODE`.

#### 2b. Exchange Code for Access Token

```bash
curl -X POST https://www.linkedin.com/oauth/v2/accessToken \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "grant_type=authorization_code" \
  -d "code=AUTH_CODE" \
  -d "redirect_uri=YOUR_REDIRECT_URI" \
  -d "client_id=YOUR_CLIENT_ID" \
  -d "client_secret=YOUR_CLIENT_SECRET"
```

Response:
```json
{
  "access_token": "AQX...",
  "expires_in": 5183944,
  "refresh_token": "AQV...",
  "refresh_token_expires_in": 31536000
}
```

#### 2c. Get Your Person URN

```bash
curl -H "Authorization: Bearer ACCESS_TOKEN" \
     https://api.linkedin.com/v2/me
```

Your URN is `urn:li:person:{id}` where `id` is from the response.

### Step 3 — Configure Environment

```bash
# Windows
set LINKEDIN_ACCESS_TOKEN=AQX...
set LINKEDIN_PERSON_URN=urn:li:person:YOUR_ID

# Or in PowerShell
$env:LINKEDIN_ACCESS_TOKEN = "AQX..."
$env:LINKEDIN_PERSON_URN = "urn:li:person:YOUR_ID"
```

### Step 4 — Enable Live Mode

In `index.js`, change:
```js
const SIMULATION_MODE = true;
// →
const SIMULATION_MODE = false;
```

Then uncomment the `PRODUCTION_ONLY` blocks in `publishToLinkedIn()`.

---

## LinkedIn Posts API Reference

### Create a Post (UGC Posts v2)

```bash
POST https://api.linkedin.com/v2/ugcPosts
Authorization: Bearer {ACCESS_TOKEN}
Content-Type: application/json
X-Restli-Protocol-Version: 2.0.0
```

```json
{
  "author": "urn:li:person:YOUR_ID",
  "lifecycleState": "PUBLISHED",
  "specificContent": {
    "com.linkedin.ugc.ShareContent": {
      "shareCommentary": { "text": "Your post content here" },
      "shareMediaCategory": "NONE"
    }
  },
  "visibility": {
    "com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"
  }
}
```

**Response headers:** `X-RestLi-Id: urn:li:share:1234567890`

**Post URL:** `https://www.linkedin.com/feed/update/urn:li:share:1234567890/`

### Visibility Options

| Value | Description |
|---|---|
| `PUBLIC` | Everyone on LinkedIn and the web |
| `CONNECTIONS` | Your 1st-degree connections only |
| `LOGGED_IN` | All signed-in LinkedIn members |

### Rate Limits

| Endpoint | Limit |
|---|---|
| UGC Posts | 100 requests / day |
| Profile API | 100 requests / day |
| OAuth Token | No limit |

---

## Content Best Practices

From `linkedin_templates.json`:

1. **Hook first** — first 2 lines must earn the "see more" click
2. **White space** — use line breaks generously for mobile readability
3. **End with a question or CTA** to drive comments
4. **Best posting times**: 8–10am or 12–1pm on Tue/Wed/Thu
5. **5 targeted hashtags** outperform 30 generic ones
6. **Native video** gets 3× more reach than YouTube links
7. **Respond to comments** within the first hour

---

## File Structure

```
mcp_servers/linkedin_mcp/
├── index.js                  ← MCP server (3 tools, simulation + production code)
├── linkedin_templates.json   ← 6 post-type templates + hashtag categories
├── package.json
└── README.md

Vault/
├── Pending_Approval/
│   └── LINKEDIN_POST_{id}_{date}.md   ← approval requests
├── Plans/
│   └── LINKEDIN_SCHEDULED_{id}_{date}.md  ← scheduled post plans
└── Done/
    └── LINKEDIN_POST_{id}_{date}.md   ← completed/approved posts
```

---

## Troubleshooting

| Error | Fix |
|---|---|
| `LINKEDIN_ACCESS_TOKEN not set` | Set env var (see Step 3 above) |
| `LinkedIn API error 401` | Token expired — re-run OAuth flow |
| `LinkedIn API error 403` | Scope `w_member_social` not approved — check Developer Portal |
| `Post exceeds 3000 characters` | Shorten content or remove hashtags |
| `Scheduled time must be in the future` | Use a future ISO 8601 datetime |

---

*Generated by AI Employee Gold v1.0*
