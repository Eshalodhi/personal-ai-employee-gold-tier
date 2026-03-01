"""
AI Employee Vault - Gmail Watcher
==================================
Monitors a Gmail inbox for new unread emails and converts them
into structured markdown task files in the Needs_Action/ folder
for the AI Employee to process.

Requires:
    - credentials.json (OAuth 2.0 client credentials from Google Cloud Console)
    - Gmail API enabled in your Google Cloud project
    - Scopes: gmail.readonly, gmail.modify

First run will open a browser for OAuth consent. After that,
token.json is cached for automatic authentication.

Usage:
    python gmail_watcher.py

Press Ctrl+C to stop the watcher.
"""

import os
import re
import sys
import time
import base64
import logging
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# ============================================================
# CONFIGURATION
# ============================================================

# Path to the AI Employee Vault root directory
VAULT_PATH = os.path.dirname(os.path.abspath(__file__))

# Destination folder for generated task files
NEEDS_ACTION_PATH = os.path.join(VAULT_PATH, 'Needs_Action')

# OAuth credentials and token paths
CREDENTIALS_PATH = os.path.join(VAULT_PATH, 'credentials.json')
TOKEN_PATH = os.path.join(VAULT_PATH, 'token.json')

# Gmail API scopes
# - gmail.readonly: read email content
# - gmail.modify: mark emails as read after processing
SCOPES = [
    'https://www.googleapis.com/auth/gmail.readonly',
    'https://www.googleapis.com/auth/gmail.modify',
]

# How often to check for new emails (in seconds)
POLL_INTERVAL = 300  # 5 minutes

# Whether to mark emails as read after processing
MARK_AS_READ = True

# Gmail label filters — fetch emails matching ANY of these labels
TARGET_LABELS = ['INBOX', 'IMPORTANT']

# Emergency keywords that trigger high priority
EMERGENCY_KEYWORDS = ['urgent', 'asap', 'critical', 'important', 'deadline', 'emergency']

# ============================================================
# LOGGING SETUP
# ============================================================

logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s: %(message)s',
    datefmt='%H:%M:%S',
)
logger = logging.getLogger('gmail_watcher')

# ============================================================
# AUTHENTICATION
# ============================================================


def authenticate():
    """
    Handle Gmail API OAuth 2.0 authentication.

    Flow:
    1. If token.json exists and is valid, use it.
    2. If token.json exists but is expired, refresh it.
    3. If no token.json, run the full OAuth consent flow
       (opens browser for user to grant access).

    Returns:
        google.oauth2.credentials.Credentials: Valid credentials object.
    """
    creds = None

    # Check for existing token
    if os.path.exists(TOKEN_PATH):
        creds = Credentials.from_authorized_user_file(TOKEN_PATH, SCOPES)
        logger.info("Loaded existing token from token.json")

    # If no valid credentials, authenticate
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            # Token expired — refresh it
            logger.info("Token expired, refreshing...")
            try:
                creds.refresh(Request())
                logger.info("Token refreshed successfully")
            except Exception as e:
                logger.warning("Token refresh failed: %s — re-authenticating", e)
                creds = None

        if not creds:
            # No valid token at all — run full OAuth flow
            if not os.path.exists(CREDENTIALS_PATH):
                logger.error("credentials.json not found at: %s", CREDENTIALS_PATH)
                logger.error("Download OAuth credentials from Google Cloud Console.")
                sys.exit(1)

            logger.info("Starting OAuth consent flow (browser will open)...")
            flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_PATH, SCOPES)
            creds = flow.run_local_server(port=0)
            logger.info("Authentication successful")

        # Save the token for future runs
        with open(TOKEN_PATH, 'w') as token_file:
            token_file.write(creds.to_json())
        logger.info("Token saved to token.json")

    return creds


# ============================================================
# EMAIL FETCHING
# ============================================================


def get_unread_emails(service):
    """
    Fetch unread emails from Gmail matching target labels.

    Uses the Gmail API users.messages.list with a query for
    unread messages, then fetches full details for each message.

    Args:
        service: Gmail API service object.

    Returns:
        list[dict]: List of message detail dicts, or empty list.
    """
    try:
        # Build query: unread emails in target labels
        label_query = ' OR '.join(f'label:{label}' for label in TARGET_LABELS)
        query = f'is:unread ({label_query})'

        results = service.users().messages().list(
            userId='me',
            q=query,
            maxResults=20,
        ).execute()

        messages = results.get('messages', [])

        if not messages:
            return []

        logger.info("Found %d unread email(s)", len(messages))

        # Fetch full details for each message
        detailed_messages = []
        for msg_ref in messages:
            msg = service.users().messages().get(
                userId='me',
                id=msg_ref['id'],
                format='full',
            ).execute()
            detailed_messages.append(msg)

        return detailed_messages

    except HttpError as e:
        logger.error("Gmail API error fetching emails: %s", e)
        return []


# ============================================================
# EMAIL PARSING
# ============================================================


def extract_header(headers, name):
    """Extract a specific header value from Gmail message headers."""
    for header in headers:
        if header['name'].lower() == name.lower():
            return header['value']
    return ''


def parse_email(message):
    """
    Parse a Gmail API message object into a structured dict.

    Extracts sender, subject, snippet, timestamp, and message ID.
    Determines priority based on emergency keywords in the subject.

    Args:
        message: Gmail API message dict (format='full').

    Returns:
        dict: Parsed email data with keys:
            id, sender, subject, snippet, timestamp, priority, labels
    """
    headers = message.get('payload', {}).get('headers', [])

    sender = extract_header(headers, 'From')
    subject = extract_header(headers, 'Subject') or '(no subject)'
    date_str = extract_header(headers, 'Date')

    # Parse the email timestamp
    try:
        email_dt = parsedate_to_datetime(date_str)
        timestamp = email_dt.strftime('%Y-%m-%dT%H:%M:%SZ')
    except Exception:
        timestamp = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')

    # Get the snippet (short preview of email body)
    snippet = message.get('snippet', '')

    # Determine priority from subject line
    subject_lower = subject.lower()
    priority = 'normal'
    for keyword in EMERGENCY_KEYWORDS:
        if keyword in subject_lower:
            priority = 'high'
            break

    # Get label IDs
    labels = message.get('labelIds', [])

    return {
        'id': message['id'],
        'sender': sender,
        'subject': subject,
        'snippet': snippet,
        'timestamp': timestamp,
        'priority': priority,
        'labels': labels,
    }


# ============================================================
# TASK FILE CREATION
# ============================================================


def sanitize_filename(text, max_length=50):
    """
    Convert arbitrary text into a safe filename component.

    Replaces spaces and special characters with underscores,
    removes consecutive underscores, and truncates to max_length.
    """
    # Replace spaces and common separators with underscores
    text = re.sub(r'[\s\-/\\:]+', '_', text)
    # Remove anything that isn't alphanumeric or underscore
    text = re.sub(r'[^\w]', '', text)
    # Collapse multiple underscores
    text = re.sub(r'_+', '_', text)
    # Strip leading/trailing underscores
    text = text.strip('_')
    # Truncate
    return text[:max_length] if text else 'no_subject'


def create_email_task(email_data):
    """
    Create a markdown task file in Needs_Action/ for a parsed email.

    Follows the vault naming convention:
        EMAIL_[sanitized_subject]_[YYYY-MM-DD].md

    The file includes YAML frontmatter with metadata and a body
    with the email snippet and suggested actions.

    Args:
        email_data: Dict from parse_email().

    Returns:
        str: Path to the created task file, or None on failure.
    """
    date_str = datetime.now(timezone.utc).strftime('%Y-%m-%d')
    subject_slug = sanitize_filename(email_data['subject'])
    task_filename = f"EMAIL_{subject_slug}_{date_str}.md"
    task_filepath = os.path.join(NEEDS_ACTION_PATH, task_filename)

    # Avoid duplicates — if file exists, append a counter
    if os.path.exists(task_filepath):
        counter = 2
        while True:
            task_filename = f"EMAIL_{subject_slug}_{counter}_{date_str}.md"
            task_filepath = os.path.join(NEEDS_ACTION_PATH, task_filename)
            if not os.path.exists(task_filepath):
                break
            counter += 1

    # Determine suggested actions based on priority
    priority_note = ''
    if email_data['priority'] == 'high':
        priority_note = '- [ ] **HIGH PRIORITY** — Escalate or respond immediately\n'

    # Build the markdown content
    now_str = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
    markdown = f"""---
type: email
from: "{email_data['sender']}"
subject: "{email_data['subject']}"
received: {email_data['timestamp']}
processed: {now_str}
priority: {email_data['priority']}
status: pending
gmail_id: {email_data['id']}
---

# Email: {email_data['subject']}

## Sender
{email_data['sender']}

## Received
{email_data['timestamp']}

## Priority
**{email_data['priority'].upper()}**

## Email Preview
> {email_data['snippet']}

## Suggested Actions
{priority_note}- [ ] Review email content
- [ ] Determine if response is needed
- [ ] Draft response (save to Pending_Approval/ if sending)
- [ ] Update Dashboard
- [ ] Move to Done when complete
- [ ] Create log entry

## Notes
_Automatically generated by gmail_watcher.py_
_Gmail labels: {', '.join(email_data['labels'])}_
"""

    try:
        with open(task_filepath, 'w', encoding='utf-8') as f:
            f.write(markdown)
        logger.info("Task created: %s", task_filename)
        logger.info("  → From: %s", email_data['sender'])
        logger.info("  → Subject: %s", email_data['subject'])
        logger.info("  → Priority: %s", email_data['priority'])
        return task_filepath
    except Exception as e:
        logger.error("Failed to create task file: %s", e)
        return None


# ============================================================
# EMAIL POST-PROCESSING
# ============================================================


def mark_as_read(service, message_id):
    """
    Mark a Gmail message as read by removing the UNREAD label.

    Args:
        service: Gmail API service object.
        message_id: Gmail message ID string.
    """
    try:
        service.users().messages().modify(
            userId='me',
            id=message_id,
            body={'removeLabelIds': ['UNREAD']},
        ).execute()
        logger.info("  → Marked as read (Gmail ID: %s)", message_id)
    except HttpError as e:
        logger.error("Failed to mark email as read: %s", e)


# ============================================================
# MAIN POLLING LOOP
# ============================================================


def poll_once(service):
    """
    Run a single poll cycle: fetch unread emails, create tasks,
    and optionally mark as read.

    Args:
        service: Gmail API service object.

    Returns:
        int: Number of emails processed in this cycle.
    """
    emails = get_unread_emails(service)

    if not emails:
        logger.info("No new unread emails")
        return 0

    processed = 0
    for message in emails:
        email_data = parse_email(message)

        logger.info("Processing: \"%s\" from %s", email_data['subject'], email_data['sender'])

        # Create the task file in Needs_Action/
        task_path = create_email_task(email_data)

        if task_path:
            processed += 1

            # Mark as read if enabled
            if MARK_AS_READ:
                mark_as_read(service, email_data['id'])

    return processed


def main():
    """
    Main function to authenticate and start the Gmail polling loop.

    Authenticates with Gmail API, then enters an infinite loop that
    checks for new emails at the configured interval. Handles errors
    gracefully and continues running until interrupted with Ctrl+C.
    """
    # Ensure Needs_Action folder exists
    os.makedirs(NEEDS_ACTION_PATH, exist_ok=True)

    # Display startup banner
    print("=" * 60)
    print("  AI Employee Vault - Gmail Watcher")
    print("  Silver v0.1")
    print("=" * 60)

    # Authenticate with Gmail API
    logger.info("Authenticating with Gmail API...")
    creds = authenticate()
    service = build('gmail', 'v1', credentials=creds)
    logger.info("Gmail API service initialized")

    # Display configuration
    print(f"  Labels:    {', '.join(TARGET_LABELS)}")
    print(f"  Interval:  {POLL_INTERVAL}s ({POLL_INTERVAL // 60} min)")
    print(f"  Mark read: {MARK_AS_READ}")
    print(f"  Output:    {NEEDS_ACTION_PATH}")
    print(f"  Started:   {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    print()
    print("Watching for new emails... (Press Ctrl+C to stop)")
    print()

    # Initial poll immediately on startup
    try:
        count = poll_once(service)
        if count > 0:
            logger.info("Initial poll: processed %d email(s)", count)
    except Exception as e:
        logger.error("Error during initial poll: %s", e)

    # Main polling loop
    try:
        while True:
            logger.info("Next check in %d seconds...", POLL_INTERVAL)
            time.sleep(POLL_INTERVAL)

            try:
                count = poll_once(service)
                if count > 0:
                    logger.info("Processed %d email(s) this cycle", count)
            except HttpError as e:
                if e.resp.status == 401:
                    # Token expired mid-session — re-authenticate
                    logger.warning("Auth expired, re-authenticating...")
                    creds = authenticate()
                    service = build('gmail', 'v1', credentials=creds)
                    logger.info("Re-authenticated successfully")
                else:
                    logger.error("Gmail API error: %s", e)
            except Exception as e:
                logger.error("Unexpected error: %s", e)
                logger.info("Will retry next cycle...")

    except KeyboardInterrupt:
        print()
        logger.info("Watcher stopped by user.")
        print("Shutting down...")
        print("Gmail watcher terminated. Goodbye!")


# Entry point
if __name__ == '__main__':
    main()
