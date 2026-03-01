/**
 * AI Employee Vault - File Operations MCP Server
 * ================================================
 * Gold Tier MCP server providing file system tools for Claude Code:
 *
 *   1. search_files     — Search by name/content with glob patterns
 *   2. read_file_content — Read any vault file (txt, md, json, csv)
 *   3. create_summary   — Aggregate stats & insights across files
 *   4. organize_files   — Move, copy, rename, mkdir
 *   5. analyze_logs     — Parse logs, extract metrics & error patterns
 *
 * All paths are resolved relative to the vault root. Operations that
 * write or move files are logged to stderr for auditability.
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
import { glob } from "glob";

// ============================================================
// CONFIGURATION
// ============================================================

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

// Vault root is two levels up from mcp_servers/file_ops_mcp/
const VAULT_PATH = path.resolve(__dirname, "..", "..");

// Max file size to read into memory (10 MB)
const MAX_READ_BYTES = 10 * 1024 * 1024;

// Log prefix for all stderr output
const LOG_PREFIX = "[file-ops-mcp]";

// ============================================================
// UTILITIES
// ============================================================

/**
 * Emit a structured log line to stderr (captured by MCP host, not sent to client).
 * @param {"INFO"|"WARN"|"ERROR"} level
 * @param {string} message
 * @param {object} [meta]
 */
function log(level, message, meta = {}) {
  const entry = {
    ts: new Date().toISOString(),
    level,
    msg: message,
    ...meta,
  };
  process.stderr.write(`${LOG_PREFIX} ${JSON.stringify(entry)}\n`);
}

/**
 * Resolve a user-supplied path to an absolute path.
 * If the supplied path is relative it is joined to the vault root.
 * Returns the resolved absolute path.
 *
 * @param {string} userPath
 * @returns {string} absolute path
 */
function resolvePath(userPath) {
  if (path.isAbsolute(userPath)) {
    return path.normalize(userPath);
  }
  return path.resolve(VAULT_PATH, userPath);
}

/**
 * Build a standard error result object for MCP tool responses.
 * @param {string} message
 * @returns {object}
 */
function errorResult(message) {
  return {
    content: [{ type: "text", text: JSON.stringify({ status: "error", error: message }, null, 2) }],
    isError: true,
  };
}

/**
 * Build a standard success result object for MCP tool responses.
 * @param {object} data
 * @returns {object}
 */
function successResult(data) {
  return {
    content: [{ type: "text", text: JSON.stringify({ status: "success", ...data }, null, 2) }],
  };
}

/**
 * Read file stats and return a metadata object.
 * @param {string} absPath
 * @returns {Promise<object>}
 */
async function fileMetadata(absPath) {
  const stat = await fsp.stat(absPath);
  return {
    path: absPath,
    relative_path: path.relative(VAULT_PATH, absPath),
    name: path.basename(absPath),
    extension: path.extname(absPath).slice(1).toLowerCase(),
    size_bytes: stat.size,
    modified: stat.mtime.toISOString(),
    created: stat.birthtime.toISOString(),
    is_directory: stat.isDirectory(),
  };
}

// ============================================================
// TOOL IMPLEMENTATIONS
// ============================================================

// ----------------------------------------------------------
// 1. search_files
// ----------------------------------------------------------

/**
 * Search for files by name pattern (glob) and optionally by content.
 *
 * @param {object} args
 * @param {string} args.pattern       Glob pattern, e.g. "**\/*.md"
 * @param {string} [args.directory]   Root dir for search (default: vault root)
 * @param {string} [args.content]     String to search inside file contents
 * @param {boolean} [args.case_sensitive] Default false
 * @param {number} [args.limit]       Max results (default 50)
 * @returns {Promise<object>}
 */
async function searchFiles(args) {
  const {
    pattern,
    directory,
    content: contentQuery,
    case_sensitive = false,
    limit = 50,
  } = args;

  if (!pattern) return errorResult("'pattern' is required.");

  const searchRoot = directory ? resolvePath(directory) : VAULT_PATH;

  // Verify search root exists
  if (!fs.existsSync(searchRoot)) {
    return errorResult(`Directory not found: ${searchRoot}`);
  }

  log("INFO", "search_files", { pattern, searchRoot, contentQuery });

  let matches;
  try {
    matches = await glob(pattern, {
      cwd: searchRoot,
      absolute: true,
      nodir: true,
      ignore: ["**/node_modules/**", "**/.git/**", "**/.obsidian/**"],
    });
  } catch (err) {
    log("ERROR", "glob failed", { error: err.message });
    return errorResult(`Glob pattern error: ${err.message}`);
  }

  // Apply content filter if requested
  let results = [];
  const queryLower = contentQuery
    ? case_sensitive
      ? contentQuery
      : contentQuery.toLowerCase()
    : null;

  for (const absPath of matches) {
    if (results.length >= limit) break;

    let meta;
    try {
      meta = await fileMetadata(absPath);
    } catch {
      continue;
    }

    if (queryLower) {
      // Skip large files for content search
      if (meta.size_bytes > MAX_READ_BYTES) {
        continue;
      }
      try {
        const raw = await fsp.readFile(absPath, "utf8");
        const haystack = case_sensitive ? raw : raw.toLowerCase();
        if (!haystack.includes(queryLower)) continue;

        // Extract up to 3 matching lines for context
        const lines = raw.split("\n");
        const matchingLines = lines
          .map((line, i) => ({ line: line.trim(), num: i + 1 }))
          .filter(({ line }) =>
            case_sensitive
              ? line.includes(contentQuery)
              : line.toLowerCase().includes(queryLower)
          )
          .slice(0, 3);

        results.push({ ...meta, matching_lines: matchingLines });
      } catch {
        continue;
      }
    } else {
      results.push(meta);
    }
  }

  return successResult({
    query: { pattern, directory: searchRoot, content: contentQuery },
    total_found: results.length,
    limited_to: limit,
    files: results,
  });
}

// ----------------------------------------------------------
// 2. read_file_content
// ----------------------------------------------------------

/**
 * Read the full content of a file. Handles txt, md, json, csv formats.
 *
 * @param {object} args
 * @param {string} args.file_path     Path to file (relative to vault or absolute)
 * @param {number} [args.max_lines]   Truncate to N lines (default: no limit)
 * @returns {Promise<object>}
 */
async function readFileContent(args) {
  const { file_path, max_lines } = args;

  if (!file_path) return errorResult("'file_path' is required.");

  const absPath = resolvePath(file_path);

  if (!fs.existsSync(absPath)) {
    return errorResult(`File not found: ${absPath}`);
  }

  let stat;
  try {
    stat = await fsp.stat(absPath);
  } catch (err) {
    return errorResult(`Cannot stat file: ${err.message}`);
  }

  if (stat.isDirectory()) {
    return errorResult(`Path is a directory, not a file: ${absPath}`);
  }

  if (stat.size > MAX_READ_BYTES) {
    return errorResult(
      `File too large to read (${stat.size} bytes). Max is ${MAX_READ_BYTES} bytes.`
    );
  }

  log("INFO", "read_file_content", { absPath, size: stat.size });

  let raw;
  try {
    raw = await fsp.readFile(absPath, "utf8");
  } catch (err) {
    return errorResult(`Cannot read file: ${err.message}`);
  }

  const ext = path.extname(absPath).slice(1).toLowerCase();
  const meta = await fileMetadata(absPath);

  // Format-specific processing
  let content = raw;
  let parsed = null;
  let formatNote = null;

  if (ext === "json") {
    try {
      parsed = JSON.parse(raw);
      content = JSON.stringify(parsed, null, 2);
      formatNote = "JSON — pretty-printed";
    } catch {
      formatNote = "JSON — parse failed, returning raw";
    }
  } else if (ext === "csv") {
    const rows = raw.trim().split("\n").map((r) => r.split(","));
    const headers = rows[0] || [];
    const dataRows = rows.slice(1);
    formatNote = `CSV — ${headers.length} columns, ${dataRows.length} data rows`;
  }

  const lines = content.split("\n");
  const truncated = max_lines && lines.length > max_lines;
  const outputLines = truncated ? lines.slice(0, max_lines) : lines;

  return successResult({
    ...meta,
    format: ext || "text",
    format_note: formatNote,
    line_count: lines.length,
    word_count: content.split(/\s+/).filter(Boolean).length,
    truncated,
    content: outputLines.join("\n"),
  });
}

// ----------------------------------------------------------
// 3. create_summary
// ----------------------------------------------------------

/**
 * Summarize one or more files — aggregate stats and generate insights.
 *
 * @param {object} args
 * @param {string[]} [args.file_paths]  Explicit list of paths
 * @param {string} [args.directory]     Summarize all files in a directory
 * @param {string} [args.pattern]       Glob to filter files (used with directory)
 * @returns {Promise<object>}
 */
async function createSummary(args) {
  const { file_paths, directory, pattern = "**/*" } = args;

  let targets = [];

  if (file_paths && file_paths.length > 0) {
    targets = file_paths.map(resolvePath);
  } else if (directory) {
    const searchRoot = resolvePath(directory);
    if (!fs.existsSync(searchRoot)) {
      return errorResult(`Directory not found: ${searchRoot}`);
    }
    targets = await glob(pattern, {
      cwd: searchRoot,
      absolute: true,
      nodir: true,
      ignore: ["**/node_modules/**", "**/.git/**"],
    });
  } else {
    return errorResult("Either 'file_paths' or 'directory' is required.");
  }

  log("INFO", "create_summary", { count: targets.length });

  let totalSize = 0;
  let totalLines = 0;
  let totalWords = 0;
  const byExtension = {};
  const perFile = [];
  const insights = [];

  for (const absPath of targets) {
    if (!fs.existsSync(absPath)) continue;

    let stat;
    try {
      stat = await fsp.stat(absPath);
    } catch {
      continue;
    }
    if (stat.isDirectory()) continue;

    const ext = path.extname(absPath).slice(1).toLowerCase() || "no-ext";
    byExtension[ext] = (byExtension[ext] || 0) + 1;
    totalSize += stat.size;

    const fileSummary = {
      path: path.relative(VAULT_PATH, absPath),
      name: path.basename(absPath),
      size_bytes: stat.size,
      modified: stat.mtime.toISOString(),
    };

    // Read content for text files under size limit
    if (stat.size <= MAX_READ_BYTES) {
      try {
        const raw = await fsp.readFile(absPath, "utf8");
        const lines = raw.split("\n").length;
        const words = raw.split(/\s+/).filter(Boolean).length;
        totalLines += lines;
        totalWords += words;
        fileSummary.line_count = lines;
        fileSummary.word_count = words;

        // Extract first non-empty line as a preview
        const preview = raw.split("\n").find((l) => l.trim().length > 0);
        if (preview) fileSummary.preview = preview.slice(0, 120);
      } catch {
        // skip content stats for unreadable files
      }
    }

    perFile.push(fileSummary);
  }

  // Generate insights
  if (perFile.length === 0) {
    insights.push("No readable files found.");
  } else {
    insights.push(`${perFile.length} files, ${(totalSize / 1024).toFixed(1)} KB total.`);
    insights.push(`${totalLines.toLocaleString()} total lines, ${totalWords.toLocaleString()} total words.`);

    // Most common extension
    const topExt = Object.entries(byExtension).sort((a, b) => b[1] - a[1])[0];
    if (topExt) insights.push(`Most common type: .${topExt[0]} (${topExt[1]} files).`);

    // Largest file
    const largest = [...perFile].sort((a, b) => b.size_bytes - a.size_bytes)[0];
    if (largest) insights.push(`Largest file: ${largest.name} (${(largest.size_bytes / 1024).toFixed(1)} KB).`);

    // Most recently modified
    const newest = [...perFile].sort((a, b) => new Date(b.modified) - new Date(a.modified))[0];
    if (newest) insights.push(`Most recently modified: ${newest.name} (${newest.modified.slice(0, 10)}).`);
  }

  return successResult({
    file_count: perFile.length,
    total_size_bytes: totalSize,
    total_size_kb: parseFloat((totalSize / 1024).toFixed(2)),
    total_lines: totalLines,
    total_words: totalWords,
    by_extension: byExtension,
    insights,
    files: perFile,
  });
}

// ----------------------------------------------------------
// 4. organize_files
// ----------------------------------------------------------

/**
 * Move, copy, rename files, or create directory structure.
 *
 * @param {object} args
 * @param {"move"|"copy"|"rename"|"mkdir"} args.operation
 * @param {string} [args.source]       Source path
 * @param {string} [args.destination]  Destination path
 * @returns {Promise<object>}
 */
async function organizeFiles(args) {
  const { operation, source, destination } = args;

  const validOps = ["move", "copy", "rename", "mkdir"];
  if (!operation || !validOps.includes(operation)) {
    return errorResult(`'operation' must be one of: ${validOps.join(", ")}`);
  }

  if (operation === "mkdir") {
    if (!destination) return errorResult("'destination' is required for mkdir.");
    const destAbs = resolvePath(destination);
    try {
      await fsp.mkdir(destAbs, { recursive: true });
      log("INFO", "mkdir", { destAbs });
      return successResult({ operation, path: destAbs, message: `Directory created: ${destAbs}` });
    } catch (err) {
      return errorResult(`mkdir failed: ${err.message}`);
    }
  }

  // move / copy / rename all need source + destination
  if (!source) return errorResult("'source' is required.");
  if (!destination) return errorResult("'destination' is required.");

  const srcAbs = resolvePath(source);
  const destAbs = resolvePath(destination);

  if (!fs.existsSync(srcAbs)) {
    return errorResult(`Source not found: ${srcAbs}`);
  }

  // Ensure destination directory exists
  const destDir = path.dirname(destAbs);
  try {
    await fsp.mkdir(destDir, { recursive: true });
  } catch (err) {
    return errorResult(`Cannot create destination directory: ${err.message}`);
  }

  log("INFO", operation, { srcAbs, destAbs });

  try {
    if (operation === "copy") {
      await fsp.copyFile(srcAbs, destAbs);
    } else {
      // move and rename are both rename under the hood
      await fsp.rename(srcAbs, destAbs);
    }
  } catch (err) {
    // On Windows, rename across drives fails — fall back to copy+delete for move
    if (operation === "move" && err.code === "EXDEV") {
      try {
        await fsp.copyFile(srcAbs, destAbs);
        await fsp.unlink(srcAbs);
      } catch (fallbackErr) {
        return errorResult(`Cross-device move failed: ${fallbackErr.message}`);
      }
    } else {
      return errorResult(`${operation} failed: ${err.message}`);
    }
  }

  return successResult({
    operation,
    source: srcAbs,
    destination: destAbs,
    message: `${operation} completed: ${path.basename(srcAbs)} → ${destAbs}`,
    timestamp: new Date().toISOString(),
  });
}

// ----------------------------------------------------------
// 5. analyze_logs
// ----------------------------------------------------------

// Patterns for common log formats
const LOG_LEVEL_RE =
  /\b(ERROR|CRITICAL|FATAL|WARN(?:ING)?|INFO|DEBUG|TRACE)\b/i;
const TIMESTAMP_RE =
  /(\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}(?::\d{2})?|\[\d{2}:\d{2}\])/;
const DASHBOARD_ENTRY_RE = /^\[(\d{2}:\d{2})\]\s+(.+)$/;

/**
 * Parse log files, extract metrics and identify patterns/errors.
 *
 * @param {object} args
 * @param {string} args.log_path       File or directory of logs
 * @param {string} [args.pattern]      Glob for directory scan (default: "*.md,*.log,*.txt")
 * @param {string} [args.filter]       Only include lines containing this string
 * @returns {Promise<object>}
 */
async function analyzeLogs(args) {
  const { log_path, pattern = "**/*.{md,log,txt}", filter } = args;

  if (!log_path) return errorResult("'log_path' is required.");

  const absPath = resolvePath(log_path);

  if (!fs.existsSync(absPath)) {
    return errorResult(`Path not found: ${absPath}`);
  }

  log("INFO", "analyze_logs", { absPath, filter });

  // Collect files to analyze
  let files = [];
  const stat = await fsp.stat(absPath);
  if (stat.isDirectory()) {
    files = await glob(pattern, {
      cwd: absPath,
      absolute: true,
      nodir: true,
      ignore: ["**/node_modules/**", "**/.git/**"],
    });
  } else {
    files = [absPath];
  }

  if (files.length === 0) {
    return errorResult(`No log files found at: ${absPath}`);
  }

  // Aggregate metrics across all files
  const metrics = {
    total_files: files.length,
    total_lines: 0,
    error_count: 0,
    warning_count: 0,
    info_count: 0,
    debug_count: 0,
    unclassified_count: 0,
  };

  const errorMessages = {}; // error text -> count
  const patterns = {};     // detected pattern -> count
  let earliest = null;
  let latest = null;
  const perFile = [];

  const filterLower = filter ? filter.toLowerCase() : null;

  for (const filePath of files) {
    let raw;
    try {
      const s = await fsp.stat(filePath);
      if (s.size > MAX_READ_BYTES) continue;
      raw = await fsp.readFile(filePath, "utf8");
    } catch {
      continue;
    }

    const lines = raw.split("\n");
    const fileStat = {
      file: path.relative(VAULT_PATH, filePath),
      line_count: lines.length,
      errors: 0,
      warnings: 0,
      infos: 0,
    };

    for (const line of lines) {
      const trimmed = line.trim();
      if (!trimmed) continue;
      metrics.total_lines++;

      // Apply filter
      if (filterLower && !trimmed.toLowerCase().includes(filterLower)) continue;

      // Extract timestamp range
      const tsMatch = trimmed.match(TIMESTAMP_RE);
      if (tsMatch) {
        const ts = tsMatch[1];
        if (!earliest || ts < earliest) earliest = ts;
        if (!latest || ts > latest) latest = ts;
      }

      // Classify by log level
      const levelMatch = trimmed.match(LOG_LEVEL_RE);
      const level = levelMatch ? levelMatch[1].toUpperCase() : null;

      if (level === "ERROR" || level === "CRITICAL" || level === "FATAL") {
        metrics.error_count++;
        fileStat.errors++;
        // Capture error message (up to 100 chars, strip timestamp prefix)
        const errText = trimmed.replace(TIMESTAMP_RE, "").replace(LOG_LEVEL_RE, "").trim().slice(0, 100);
        if (errText) errorMessages[errText] = (errorMessages[errText] || 0) + 1;
      } else if (level === "WARN" || level === "WARNING") {
        metrics.warning_count++;
        fileStat.warnings++;
      } else if (level === "INFO") {
        metrics.info_count++;
        fileStat.infos++;
      } else if (level === "DEBUG" || level === "TRACE") {
        metrics.debug_count++;
      } else {
        metrics.unclassified_count++;
        // Try dashboard-style "[HH:MM] action" entries
        const dashMatch = trimmed.match(DASHBOARD_ENTRY_RE);
        if (dashMatch) {
          const action = dashMatch[2].slice(0, 60);
          patterns[action] = (patterns[action] || 0) + 1;
        }
      }
    }

    perFile.push(fileStat);
  }

  // Top 10 errors by frequency
  const topErrors = Object.entries(errorMessages)
    .sort((a, b) => b[1] - a[1])
    .slice(0, 10)
    .map(([msg, count]) => ({ count, message: msg }));

  // Top 5 recurring patterns
  const topPatterns = Object.entries(patterns)
    .sort((a, b) => b[1] - a[1])
    .slice(0, 5)
    .map(([pattern, count]) => ({ count, pattern }));

  // Health assessment
  const health =
    metrics.error_count === 0
      ? "HEALTHY"
      : metrics.error_count < 5
      ? "DEGRADED"
      : "CRITICAL";

  return successResult({
    ...metrics,
    health,
    time_range: { earliest, latest },
    top_errors: topErrors,
    recurring_patterns: topPatterns,
    per_file: perFile,
    filter_applied: filter || null,
  });
}

// ============================================================
// MCP SERVER SETUP
// ============================================================

const server = new Server(
  {
    name: "file-ops-mcp-server",
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
        name: "search_files",
        description:
          "Search for files in the vault by name pattern (glob) and optionally by content. " +
          "Returns file paths, metadata, and matching line previews.",
        inputSchema: {
          type: "object",
          properties: {
            pattern: {
              type: "string",
              description: "Glob pattern to match file names, e.g. '**/*.md' or 'Needs_Action/*'",
            },
            directory: {
              type: "string",
              description: "Directory to search within (relative to vault root). Default: vault root.",
            },
            content: {
              type: "string",
              description: "Optional string to search inside file contents.",
            },
            case_sensitive: {
              type: "boolean",
              description: "Whether content search is case-sensitive. Default: false.",
            },
            limit: {
              type: "number",
              description: "Maximum number of results to return. Default: 50.",
            },
          },
          required: ["pattern"],
        },
      },
      {
        name: "read_file_content",
        description:
          "Read the full content of any file in the vault. Handles .txt, .md, .json (pretty-printed), " +
          "and .csv formats. Returns content plus metadata (size, lines, word count).",
        inputSchema: {
          type: "object",
          properties: {
            file_path: {
              type: "string",
              description: "Path to the file, relative to vault root or absolute.",
            },
            max_lines: {
              type: "number",
              description: "Truncate output to this many lines. Omit for full file.",
            },
          },
          required: ["file_path"],
        },
      },
      {
        name: "create_summary",
        description:
          "Summarize one or more files or an entire directory. Returns aggregate stats " +
          "(file count, total size, lines, words), per-file details, and auto-generated insights.",
        inputSchema: {
          type: "object",
          properties: {
            file_paths: {
              type: "array",
              items: { type: "string" },
              description: "List of file paths to summarize. Use this OR 'directory'.",
            },
            directory: {
              type: "string",
              description: "Summarize all files in this directory. Use this OR 'file_paths'.",
            },
            pattern: {
              type: "string",
              description: "Glob to filter files when using 'directory'. Default: '**/*'.",
            },
          },
        },
      },
      {
        name: "organize_files",
        description:
          "Move, copy, or rename files between vault folders, or create new directory structure. " +
          "All paths are resolved relative to the vault root.",
        inputSchema: {
          type: "object",
          properties: {
            operation: {
              type: "string",
              enum: ["move", "copy", "rename", "mkdir"],
              description: "Operation to perform.",
            },
            source: {
              type: "string",
              description: "Source file path (not needed for mkdir).",
            },
            destination: {
              type: "string",
              description: "Destination file or directory path.",
            },
          },
          required: ["operation"],
        },
      },
      {
        name: "analyze_logs",
        description:
          "Parse log files to extract metrics, identify error patterns, and assess system health. " +
          "Accepts a single log file or a directory of logs. Returns counts by level, top errors, " +
          "recurring patterns, and a health status (HEALTHY / DEGRADED / CRITICAL).",
        inputSchema: {
          type: "object",
          properties: {
            log_path: {
              type: "string",
              description: "Path to a log file or directory containing logs.",
            },
            pattern: {
              type: "string",
              description: "Glob to match log files when 'log_path' is a directory. Default: '**/*.{md,log,txt}'.",
            },
            filter: {
              type: "string",
              description: "Only include log lines containing this string.",
            },
          },
          required: ["log_path"],
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

  log("INFO", `tool called: ${name}`, { args });

  try {
    switch (name) {
      case "search_files":
        return await searchFiles(args);

      case "read_file_content":
        return await readFileContent(args);

      case "create_summary":
        return await createSummary(args);

      case "organize_files":
        return await organizeFiles(args);

      case "analyze_logs":
        return await analyzeLogs(args);

      default:
        return errorResult(
          `Unknown tool: "${name}". Available tools: search_files, read_file_content, create_summary, organize_files, analyze_logs`
        );
    }
  } catch (err) {
    // Catch-all for unexpected errors — prevents server crash
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
  log("INFO", "File Ops MCP Server started", { vault: VAULT_PATH });
}

main().catch((err) => {
  process.stderr.write(`${LOG_PREFIX} FATAL: ${err.message}\n`);
  process.exit(1);
});
