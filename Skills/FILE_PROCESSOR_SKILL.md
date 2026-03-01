---
skill_name: FILE_PROCESSOR
version: 1.0
category: core
created: 2026-02-15
---

# Agent Skill: File Processor

## Purpose
Process pending files from Needs_Action folder, analyze them, update Dashboard, and move to Done.

## Trigger
Manual execution via Claude Code command

## Input Requirements
- Files in Needs_Action/ folder
- Files must have markdown frontmatter

## Process Steps

### 1. Discovery
- List all .md files in Needs_Action/
- Sort by priority then by timestamp
- Count total files to process

### 2. For Each File

#### a. Read & Extract
- Open file
- Parse frontmatter (type, original_name, status, priority)
- Read content body
- Extract key information

#### b. Analyze
- Determine file category
- Check for emergency keywords (urgent, asap, critical)
- Identify required actions

#### c. Update Dashboard
- Open Dashboard.md
- Update 'Pending Actions' (decrement by 1)
- Update 'Completed Tasks' (increment by 1)
- Add entry to 'Recent Activity' section
- Format: [HH:MM] Processed [filename]: [brief description]
- Update 'Last Updated' timestamp
- Save Dashboard.md

#### d. Move File
- Create destination path: Done/[filename]
- Move file from Needs_Action/ to Done/
- Verify move successful

#### e. Log Action
- Open or create Logs/[YYYY-MM-DD].md
- Append log entry with timestamp, action, file, status

### 3. Completion
- Count total files processed
- Update Dashboard Quick Stats
- Create summary log entry

## Safety Rules

1. **NEVER delete files** - only move them
2. **ALWAYS verify** file exists before processing
3. **ALWAYS log** each action
4. **VERIFY move** was successful before updating Dashboard
5. **If error occurs:** Leave file in Needs_Action and log error

## Example Workflow

Input: Needs_Action/FILE_test_document_2026-02-15.md

Actions:
1. Read file → Extract metadata
2. Analyze → Determine actions needed
3. Update Dashboard → Add activity entry
4. Move → Done/FILE_test_document_2026-02-15.md
5. Log → Entry created in Logs/2026-02-15.md

Output:
- Dashboard updated ✓
- File in Done/ ✓
- Log entry created ✓

---
*Skill Version: 1.0*
