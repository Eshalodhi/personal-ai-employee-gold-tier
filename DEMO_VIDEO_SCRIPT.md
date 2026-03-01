# Demo Video Script — Personal AI Employee (Gold Tier)

**Target Length:** 8–10 minutes
**Format:** Screen recording + voiceover (or live commentary)
**Tools on screen:** Terminal (Windows Terminal) · Obsidian · VS Code

---

## Before You Record

### Setup Checklist

```bash
# 1. Verify all MCP servers installed
ls mcp_servers/*/node_modules -d

# 2. Check Ralph state — should show 8+ cycles
cat Logs/ralph/ralph_state.json

# 3. Confirm Done/ has 117+ files
# 4. Confirm Reports/ has CEO briefings
ls Reports/

# 5. Open Obsidian with AI_Employee_Vault as vault
# 6. Set terminal font size to 18+ (legible on 1080p)
# 7. Use dark terminal theme (Dracula or One Dark)
# 8. Record at 1920x1080, 30fps minimum
# 9. Silence Windows notifications (Focus Assist ON)
```

### Recording Tips
- **Slow down** — type commands deliberately, pause 2 sec after each output
- **Zoom in** on key output lines before moving on
- **Highlight with mouse** over important lines as you speak
- **Don't edit out** Ralph's autonomy — let it run; it's the proof
- **Silence pauses** in post-editing — keep energy up

---

## INTRO — 0:00 to 1:00 (60 seconds)

### Screen: Dashboard.md open in Obsidian

**SAY:**

> "Hi, I'm Esha Khan, and this is my Gold tier submission for the Personal AI Employee hackathon.
>
> What you're looking at is the AI Employee Vault — a fully autonomous, local-first system that acts as a digital employee: reading emails, triaging tasks, posting to social media, briefing executives, and integrating personal and business workflows.
>
> Let me show you the numbers."

### Action: Point cursor to each stat in Dashboard.md as you say it

**SAY:**

> "Nine out of ten Gold requirements complete. Forty-plus hours of work. One hundred and seventeen tasks completed autonomously. Five MCP servers. Twenty-nine tools. Ten agent skills. Four social media platforms. Eight-plus autonomous OODA cycles with zero errors.
>
> The one requirement I didn't complete is Odoo ERP integration — I made a deliberate call to go deeper on cross-domain integration instead. More on that in Part 7."

### Transition: "Here's how it all fits together."

---

## PART 1: Architecture Overview — 1:00 to 2:30 (90 seconds)

### Screen: README.md — Architecture ASCII diagram (zoom in)

**SAY:**

> "The system has three layers.
>
> At the top — the personal domain. Gmail is monitored by a Python watcher that converts every email into a structured markdown task file. Files dropped into the vault are caught by a filesystem watcher. Everything flows into Needs_Action."

### Action: Point to the PERSONAL DOMAIN section

**SAY:**

> "In the middle — Ralph Wiggum, the autonomous OODA loop. Observe, Orient, Decide, Act, Reflect. Runs every five minutes, making decisions without human prompting."

### Action: Point to the RALPH section

**SAY:**

> "Below Ralph — five MCP servers giving Claude Code twenty-nine real tools. Email, file operations, social media across four platforms, Google Workspace, and Slack for team communication."

### Screen: .claude/mcp_config.json

```bash
cat .claude/mcp_config.json
```

**SAY:**

> "All five servers registered here. Claude Code loads them automatically on startup. And ten agent skills — markdown files Claude reads as instructions — define every capability in the system."

### Transition: "Let me show you the brain of this system — Ralph."

---

## PART 2: Ralph Wiggum Autonomous Loop — 2:30 to 4:30 (120 seconds)

### Screen: Terminal

```bash
python ralph_wiggum_loop.py --once
```

**SAY:** "Ralph uses the OODA loop. Watch the output."

### Action: Narrate each phase as it prints:

**OBSERVE phase:**
> "Observe — Ralph scans the vault. Needs_Action has incoming emails. Pending_Approval has items waiting. Ralph builds a complete picture of system state."

**ORIENT phase:**
> "Orient — Ralph classifies what matters. Urgent keywords trigger high priority. Expiring approvals get escalated. This is the decision intelligence layer."

**DECIDE phase:**
> "Decide — Ralph scores each possible action and builds a priority-ordered plan. Notice it creates a plan file first — that's the PLAN_CREATOR_SKILL running automatically."

**ACT phase:**
> "Act — Ralph executes. If there are approved items, it calls the MCP tool. Every external write goes through a HITL approval file first — Ralph never bypasses human oversight."

**REFLECT phase:**
> "Reflect — Ralph logs every decision, updates the dashboard, and saves state. Eight-plus cycles with zero errors."

### Screen: Show ralph_state.json

```bash
cat Logs/ralph/ralph_state.json
```

**SAY:**

> "Persistent state across restarts. Cycle count, last run timestamp, last action. Ralph remembers what it did last time and avoids duplicate actions."

### Screen: Open today's log in Obsidian (Logs/YYYY-MM-DD.md)

**SAY:**

> "Every Ralph decision logged here with ISO 8601 timestamps. The full history of every autonomous action Ralph has ever taken. Nothing deleted — everything traceable."

### Transition: "Ralph is monitoring Gmail too. Let me show you that integration."

---

## PART 3: Gmail Integration — 4:30 to 6:00 (90 seconds)

### Screen: Terminal

```bash
python gmail_watcher.py
```

**SAY:**

> "The Gmail watcher polls every five minutes using OAuth 2.0. It reads subject lines, sender addresses, and body snippets — then converts each email into a structured task file with priority classification."

### Action: Point to the output lines showing emails detected

**SAY:**

> "Security alerts become URGENT. CI failures become HIGH. Newsletters get PROMOTIONAL. The AI reads the context, not just the subject line."

### Screen: Open one EMAIL_*.md file from Needs_Action/ in Obsidian

**SAY:**

> "This is what the AI Employee sees. Sender, priority, subject, full body — ready for Ralph to process in the next OODA cycle."

### Screen: Show Done/ folder with 117+ EMAIL files

**SAY:**

> "One hundred and ten emails processed autonomously in one session. Every one classified, logged, and actioned or moved to Done. The inbox is no longer overwhelming — it's a managed queue."

### Transition: "But the AI never acts on your behalf without asking first. That's the HITL workflow."

---

## PART 4: HITL Approval Workflow — 6:00 to 7:30 (90 seconds)

### Screen: Terminal

```bash
claude "Draft a summary email to the team about AI Employee progress and create an approval request to send it"
```

**SAY:**

> "Watch what happens when the AI wants to take an external action — send an email, post to social media, create a calendar event. It never does it directly."

### Action: Wait for Claude to create the file, then show Pending_Approval/

**SAY:**

> "It creates an approval file. The action is completely described — who it would send to, exact content, risk level, expiry time. A human can read this in thirty seconds and decide."

### Screen: Open the APPROVAL_*.md file

**SAY:**

> "This is the approval contract between the AI and the human. The AI proposes. The human decides. No external action ever happens without this gate."

### Action: In Obsidian, drag the file from Pending_Approval/ to Approved/

**SAY:** "I move the file to Approved. That's the entire human interaction. One file move."

### Screen: Terminal

```bash
claude "Check Approved folder and execute all pending approvals"
```

**SAY:**

> "The AI detects the approval, executes via the Email MCP Server, and archives everything to Done. Full audit trail. This is how the AI stays trustworthy."

### Transition: "Let me show you the executive layer — the CEO briefing."

---

## PART 5: CEO Briefing — 7:30 to 8:30 (60 seconds)

### Screen: Open Reports/ in Obsidian, click a CEO briefing file

**SAY:** "Every week, the AI Employee generates a full executive briefing automatically."

### Action: Scroll slowly through each section as you narrate:

> "Executive summary — key highlights, critical actions, wins from the week.
>
> Email intelligence — how many arrived, how classified, which needed urgent action.
>
> Task metrics — completed, pending, approval pipeline status.
>
> System performance — Ralph's cycle stats, MCP tool usage, errors.
>
> Upcoming week preview — what Ralph will focus on next."

### Screen: Run the generator

```bash
python weekly_ceo_briefing.py
```

**SAY:** "One command. Seven days of vault analytics. A briefing a real executive could act on."

### Transition: "Now the social media layer and MCP servers in action."

---

## PART 6: Social Media & MCP Servers — 8:30 to 10:00 (90 seconds)

### Screen: Terminal

```bash
python social_media_auto_poster.py --status
```

**SAY:**

> "Four social media platforms — LinkedIn, Twitter, Instagram, Facebook. All in simulation mode for this demo — full workflow, zero live API calls."

```bash
python social_media_auto_poster.py --generate --platform linkedin --dry-run
```

**SAY:**

> "Platform-specific content generation. Different character limits, different hashtag strategies, different tone per platform. Quality gates run automatically — if the post is too long or missing a call-to-action, it's flagged before the approval file is created."

### Screen: Terminal — Claude using MCP directly

```bash
claude "Use the social_media MCP server to generate a thought leadership post about autonomous AI employees"
```

**SAY:**

> "Or Claude uses the twelve MCP tools directly in conversation. Create posts, schedule them, cross-post across platforms. All gated. All logged. The social_media_mcp alone has twelve tools."

### Transition: "And now the piece I'm most proud of — cross-domain integration."

---

## PART 7: Cross-Domain Integration — 10:00 to 11:00 (60 seconds)

### Screen: Terminal

```bash
python cross_domain_integration_demo.py --workflow all --dry-run
```

**SAY:** "Three workflows bridging personal and business domains."

### Action: Narrate each workflow as it prints:

**Workflow 1:**
> "An urgent personal email triggers a cascade across three systems: a business calendar event is scheduled, the team gets a Slack notification, a briefing document is uploaded to Google Drive. Three MCP servers. Three approval files. One cohesive action."

**Workflow 2:**
> "A business calendar meeting is detected. The AI cross-references the business Gmail for context, sends a personal reminder email with a prep checklist, and sets a Slack reminder for the team lead."

**Workflow 3:**
> "The CEO briefing gets distributed. Uploaded to Google Drive, announced in the Slack leadership channel with highlights, attached as a file, and a review meeting is scheduled on the calendar."

### Action: Zoom in on the final summary line

**SAY:**

> "Nine approval files across five domains from a single command. Personal Gmail, Business Gmail, Calendar, Drive, Slack — all coordinated, all HITL-gated. This is what a real AI employee looks like."

---

## CONCLUSION — 11:00 to 11:30 (30 seconds)

### Screen: README.md — Achievement Summary table (zoom in)

**SAY:**

> "To recap: nine out of ten Gold tier requirements. Five MCP servers. Twenty-nine tools. Ten agent skills. Four social platforms. Eight-plus autonomous cycles. One hundred and seventeen tasks completed.
>
> Production-ready architecture. Simulation mode protects against accidents. Every action logged and auditable.
>
> The missing requirement is Odoo. I made a deliberate trade-off — broader cross-domain coverage over ERP integration. I stand by that call.
>
> Thank you for an incredible hackathon brief. The vault is alive. Ralph is running. The AI Employee is on the clock."

### Final shot: Obsidian vault graph view (if available) or Dashboard.md

---

## Commands Quick Reference (copy-paste ready)

```bash
# PART 1 — Architecture
cat .claude/mcp_config.json

# PART 2 — Ralph
python ralph_wiggum_loop.py --once
cat Logs/ralph/ralph_state.json

# PART 3 — Gmail
python gmail_watcher.py

# PART 4 — HITL
claude "Draft a summary email about AI Employee progress and create an approval request to send it"
claude "Check Approved folder and execute all pending approvals"

# PART 5 — CEO Briefing
python weekly_ceo_briefing.py

# PART 6 — Social Media
python social_media_auto_poster.py --status
python social_media_auto_poster.py --generate --platform linkedin --dry-run
claude "Use the social_media MCP server to generate a thought leadership post about autonomous AI employees"

# PART 7 — Cross-Domain
python cross_domain_integration_demo.py --workflow all --dry-run
```

---

## Screen Recording Checklist

### Before Recording
- [ ] Terminal font size >= 18pt, dark theme
- [ ] Obsidian open with AI_Employee_Vault vault loaded
- [ ] All MCP server `node_modules/` installed
- [ ] `Logs/ralph/ralph_state.json` shows 8+ cycles
- [ ] `Done/` has 117+ files
- [ ] `Reports/` has at least one CEO briefing
- [ ] `Needs_Action/` has EMAIL_*.md files (or gmail_watcher ready to run)
- [ ] Display 1920x1080, notifications silenced (Focus Assist ON)

### Post-Recording Editing Notes
- Cut any command-typing pauses > 3 seconds
- Add zoom + highlight effect over key output lines
- Add lower thirds for each Part title (e.g. "Part 2: Ralph Wiggum — OODA Loop")
- Add progress bar at top if possible
- Background music: soft lo-fi at 10% volume during pauses
- Export: MP4, H.264, 1080p, <= 500MB

---

*Script version: 1.0 | Gold Tier | February 2026*
*Estimated runtime: 9–11 minutes depending on terminal output speed*
