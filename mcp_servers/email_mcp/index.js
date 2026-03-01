/**
 * AI Employee Vault - Email MCP Server
 * =====================================
 * MCP server that provides a send_email tool for Claude Code
 * to send emails via the Gmail API.
 *
 * Uses OAuth 2.0 credentials (credentials.json) and cached
 * token (token.json) from the vault root directory.
 *
 * Usage:
 *   node index.js
 *
 * This server is meant to be launched by Claude Code via MCP config.
 */

import { Server } from "@modelcontextprotocol/sdk/server/index.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import {
  CallToolRequestSchema,
  ListToolsRequestSchema,
} from "@modelcontextprotocol/sdk/types.js";
import { google } from "googleapis";
import fs from "fs";
import path from "path";
import { fileURLToPath } from "url";

// ============================================================
// CONFIGURATION
// ============================================================

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

// Vault root is two levels up from mcp_servers/email_mcp/
const VAULT_PATH = path.resolve(__dirname, "..", "..");

// OAuth credential paths — shared with gmail_watcher.py
const CREDENTIALS_PATH = path.join(VAULT_PATH, "credentials.json");
const TOKEN_PATH = path.join(VAULT_PATH, "token.json");

// Gmail API scopes needed for sending
const SCOPES = [
  "https://www.googleapis.com/auth/gmail.send",
  "https://www.googleapis.com/auth/gmail.readonly",
  "https://www.googleapis.com/auth/gmail.modify",
];

// ============================================================
// GMAIL AUTHENTICATION
// ============================================================

/**
 * Load OAuth 2.0 credentials and return an authenticated Gmail client.
 *
 * Reads credentials.json for client ID/secret and token.json for
 * the cached access/refresh token. If the token is expired, it
 * refreshes automatically using the refresh token.
 *
 * @returns {Promise<object>} Authenticated Gmail API client
 * @throws {Error} If credentials or token files are missing
 */
async function getGmailClient() {
  // Verify credentials file exists
  if (!fs.existsSync(CREDENTIALS_PATH)) {
    throw new Error(
      `credentials.json not found at ${CREDENTIALS_PATH}. ` +
        "Download OAuth credentials from Google Cloud Console."
    );
  }

  // Verify token file exists (must run gmail_watcher.py first to generate)
  if (!fs.existsSync(TOKEN_PATH)) {
    throw new Error(
      `token.json not found at ${TOKEN_PATH}. ` +
        "Run gmail_watcher.py first to complete OAuth flow and generate token."
    );
  }

  // Load credentials and token
  const credentials = JSON.parse(fs.readFileSync(CREDENTIALS_PATH, "utf8"));
  const token = JSON.parse(fs.readFileSync(TOKEN_PATH, "utf8"));

  // Extract client config — handle both "installed" and "web" credential types
  const clientConfig = credentials.installed || credentials.web;
  if (!clientConfig) {
    throw new Error(
      "Invalid credentials.json format. Expected 'installed' or 'web' key."
    );
  }

  // Create OAuth2 client
  const oauth2Client = new google.auth.OAuth2(
    clientConfig.client_id,
    clientConfig.client_secret,
    clientConfig.redirect_uris?.[0] || "http://localhost"
  );

  // Set the cached token
  oauth2Client.setCredentials(token);

  // Handle automatic token refresh
  oauth2Client.on("tokens", (newTokens) => {
    // Merge new tokens with existing ones and save
    const updatedToken = { ...token, ...newTokens };
    fs.writeFileSync(TOKEN_PATH, JSON.stringify(updatedToken, null, 2));
  });

  return google.gmail({ version: "v1", auth: oauth2Client });
}

// ============================================================
// EMAIL SENDING
// ============================================================

/**
 * Build a RFC 2822 compliant email message and encode it for the Gmail API.
 *
 * Constructs the email headers (To, Cc, Bcc, Subject) and body,
 * then base64url-encodes the entire message as required by
 * the Gmail API messages.send endpoint.
 *
 * @param {string} to - Recipient email address
 * @param {string} subject - Email subject line
 * @param {string} body - Email body (plain text)
 * @param {string} [cc] - CC recipients (comma-separated)
 * @param {string} [bcc] - BCC recipients (comma-separated)
 * @returns {string} Base64url-encoded email message
 */
function buildRawEmail(to, subject, body, cc, bcc) {
  const headers = [
    `To: ${to}`,
    `Subject: ${subject}`,
    'Content-Type: text/plain; charset="UTF-8"',
    "MIME-Version: 1.0",
  ];

  if (cc) headers.push(`Cc: ${cc}`);
  if (bcc) headers.push(`Bcc: ${bcc}`);

  const message = headers.join("\r\n") + "\r\n\r\n" + body;

  // Base64url encode (Gmail API requirement)
  return Buffer.from(message)
    .toString("base64")
    .replace(/\+/g, "-")
    .replace(/\//g, "_")
    .replace(/=+$/, "");
}

/**
 * Send an email via the Gmail API.
 *
 * @param {object} gmail - Authenticated Gmail API client
 * @param {object} params - Email parameters
 * @param {string} params.to - Recipient email address
 * @param {string} params.subject - Email subject
 * @param {string} params.body - Email body (plain text)
 * @param {string} [params.cc] - CC recipients
 * @param {string} [params.bcc] - BCC recipients
 * @returns {Promise<object>} Gmail API response with message ID
 */
async function sendEmail(gmail, { to, subject, body, cc, bcc }) {
  const raw = buildRawEmail(to, subject, body, cc, bcc);

  const response = await gmail.users.messages.send({
    userId: "me",
    requestBody: { raw },
  });

  return response.data;
}

// ============================================================
// MCP SERVER SETUP
// ============================================================

const server = new Server(
  {
    name: "email-mcp-server",
    version: "1.0.0",
  },
  {
    capabilities: {
      tools: {},
    },
  }
);

// ------------------------------------------------------------
// Tool: List available tools
// ------------------------------------------------------------

server.setRequestHandler(ListToolsRequestSchema, async () => {
  return {
    tools: [
      {
        name: "send_email",
        description:
          "Send an email via Gmail API. IMPORTANT: Per Company Handbook and HITL_APPROVAL_SKILL, " +
          "sending emails requires human approval. Create an approval request in Pending_Approval/ " +
          "first, and only call this tool after the approval file has been moved to Approved/.",
        inputSchema: {
          type: "object",
          properties: {
            to: {
              type: "string",
              description: "Recipient email address",
            },
            subject: {
              type: "string",
              description: "Email subject line",
            },
            body: {
              type: "string",
              description: "Email body content (plain text)",
            },
            cc: {
              type: "string",
              description:
                "CC recipients, comma-separated (optional)",
            },
            bcc: {
              type: "string",
              description:
                "BCC recipients, comma-separated (optional)",
            },
          },
          required: ["to", "subject", "body"],
        },
      },
    ],
  };
});

// ------------------------------------------------------------
// Tool: Handle tool calls
// ------------------------------------------------------------

server.setRequestHandler(CallToolRequestSchema, async (request) => {
  const { name, arguments: args } = request.params;

  if (name !== "send_email") {
    return {
      content: [
        {
          type: "text",
          text: `Error: Unknown tool "${name}". Available tools: send_email`,
        },
      ],
      isError: true,
    };
  }

  // Validate required fields
  const { to, subject, body, cc, bcc } = args;

  if (!to || !subject || !body) {
    return {
      content: [
        {
          type: "text",
          text: "Error: Missing required fields. 'to', 'subject', and 'body' are all required.",
        },
      ],
      isError: true,
    };
  }

  // Basic email format validation
  const emailPattern = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
  const allRecipients = [to, ...(cc ? cc.split(",") : []), ...(bcc ? bcc.split(",") : [])];
  for (const addr of allRecipients) {
    const trimmed = addr.trim();
    if (!emailPattern.test(trimmed)) {
      return {
        content: [
          {
            type: "text",
            text: `Error: Invalid email address format: "${trimmed}"`,
          },
        ],
        isError: true,
      };
    }
  }

  try {
    // Authenticate and get Gmail client
    const gmail = await getGmailClient();

    // Send the email
    const result = await sendEmail(gmail, { to, subject, body, cc, bcc });

    // Build success response
    const response = {
      status: "success",
      message_id: result.id,
      thread_id: result.threadId,
      to,
      subject,
      cc: cc || null,
      bcc: bcc || null,
      timestamp: new Date().toISOString(),
    };

    return {
      content: [
        {
          type: "text",
          text: JSON.stringify(response, null, 2),
        },
      ],
    };
  } catch (error) {
    // Structured error response
    const errorResponse = {
      status: "error",
      error: error.message,
      to,
      subject,
      timestamp: new Date().toISOString(),
    };

    // Add hint for common errors
    if (error.message.includes("token.json")) {
      errorResponse.hint =
        "Run 'python gmail_watcher.py' first to complete OAuth flow.";
    } else if (error.message.includes("credentials.json")) {
      errorResponse.hint =
        "Download OAuth credentials from Google Cloud Console.";
    } else if (error.message.includes("invalid_grant")) {
      errorResponse.hint =
        "Token expired or revoked. Delete token.json and re-run gmail_watcher.py.";
    }

    return {
      content: [
        {
          type: "text",
          text: JSON.stringify(errorResponse, null, 2),
        },
      ],
      isError: true,
    };
  }
});

// ============================================================
// START SERVER
// ============================================================

async function main() {
  const transport = new StdioServerTransport();
  await server.connect(transport);
  // Server is now running and listening on stdio
}

main().catch((error) => {
  console.error("Fatal error starting MCP server:", error);
  process.exit(1);
});
