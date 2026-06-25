# Repository Polish and Documentation Update Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Clean up obsolete template boilerplate files, write a comprehensive `README.md` reflecting the actual library capabilities (StateManager, JobManager, MCP Server stdio/SSE, CLI), and ensure style conformance.

**Architecture:** Documentation and cleanup phase. Remove obsolete `src/gangway/main.py` and `tests/test_main.py`, update `README.md` with complete usage guides, and run `ruff` for code format.

**Tech Stack:** Python, Markdown, Ruff, Pytest

## Global Constraints
- Project Root Directory: `C:\Users\abdo\.gemini\antigravity\scratch\gangway`
- Package Name: `gangway`
- Run lint checks using `ruff check` and formatting using `ruff format`.
- Verify all tests pass with `pytest`.

---

### Task 1: Obsolete Files Deletion

**Files:**
- [DELETE] [main.py](file:///C:/Users/abdo/.gemini/antigravity/scratch/gangway/src/gangway/main.py)
- [DELETE] [test_main.py](file:///C:/Users/abdo/.gemini/antigravity/scratch/gangway/tests/test_main.py)

**Interfaces:**
- Consumes: None
- Produces: Cleaner repository directory tree.

- [ ] **Step 1: Delete `src/gangway/main.py`**
  Delete the obsolete boilerplate file:
  `C:\Users\abdo\.gemini\antigravity\scratch\gangway\src\gangway\main.py`

- [ ] **Step 2: Delete `tests/test_main.py`**
  Delete the obsolete boilerplate test file:
  `C:\Users\abdo\.gemini\antigravity\scratch\gangway\tests\test_main.py`

- [ ] **Step 3: Run pytest to verify no broken dependencies**
  Run: `.venv\Scripts\pytest`
  Expected: PASS (38 tests passed, `test_main.py` is no longer collected).

- [ ] **Step 4: Commit cleanup**
  ```bash
  git rm src/gangway/main.py tests/test_main.py
  git commit -m "chore: remove obsolete main.py and test_main.py boilerplate"
  ```

---

### Task 2: Rewrite README.md

**Files:**
- [MODIFY] [README.md](file:///C:/Users/abdo/.gemini/antigravity/scratch/gangway/README.md)

**Interfaces:**
- Consumes: None
- Produces: Complete and comprehensive user documentation.

- [ ] **Step 1: Replace contents of `README.md` with comprehensive documentation**
  Write complete usage guides, configuration references, CLI arguments, SSE/stdio transports, and listing of all 16 MCP tools.

  Content to write:
  ```markdown
  # Gangway

  A smart Agent-to-Server Bridge connecting AI agents (like Cursor and Claude Desktop) to remote environments (VPS, Kaggle, Colab) for full control, functioning as both an MCP server and a REST API.

  ## Features

  * **Directory State Management**: Maintains and tracks the active working directory (CWD) across execution contexts, resolving relative paths and enforcing sandbox directory checks (`allowed_root`) to prevent path traversal.
  * **Background Job Control**: Execute long-running shell commands asynchronously. Captures logs (`stdout` and `stderr`) to disk. Supports recursive process tree termination (on Unix and Windows) and prevents PID recycling exploits.
  * **Robust MCP Server**: Provides standard `stdio` transport and `SSE` (Server-Sent Events) HTTP transport modes using Starlette and Uvicorn.
  * **Bearer Token Authentication**: Enforces token authentication case-insensitively in headers or query parameters for SSE transport.
  * **Zero-Dependency Core**: Leverages the low-level `mcp` library, standard libraries, `starlette`, `uvicorn`, `psutil`, and `tomli`.

  ## Installation

  Install from your local build or PyPI:
  ```bash
  pip install gangway
  ```

  ## Configuration

  Gangway can be configured via Environment Variables, JSON/TOML configuration files, or CLI arguments (CLI arguments take the highest precedence).

  ### Configuration Parameters

  | CLI Argument | Environment Variable | Configuration Key | Default | Description |
  |--------------|----------------------|-------------------|---------|-------------|
  | `--token` | `GANGWAY_TOKEN` | `token` | `None` | Bearer token required for authentication. |
  | `--allowed-root` | `GANGWAY_ALLOWED_ROOT` | `allowed_root` | `None` | Limit directory interactions to this root path. |
  | `--port` | `GANGWAY_PORT` | `port` | `8000` | Port to run the SSE web server on. |
  | `--host` | `GANGWAY_HOST` | `host` | `127.0.0.1` | Host address to bind the SSE server to. |
  | `--transport` | - | - | `stdio` | Transport mode (`stdio` or `sse`). |

  ## CLI Usage

  To run the server using `stdio` transport:
  ```bash
  gangway --transport stdio --token secret-token --allowed-root /path/to/sandbox
  ```

  To run the server using `sse` transport:
  ```bash
  gangway --transport sse --host 127.0.0.1 --port 8000 --token secret-token --allowed-root /path/to/sandbox
  ```

  Using a configuration file:
  ```bash
  gangway --config /path/to/config.toml --transport sse
  ```

  ## Exposed MCP Tools

  Gangway exposes 16 tools to connecting AI agents:

  ### File Operations
  1. `list_directory`: Lists directory contents, returning file size and modification time.
  2. `glob_search`: Performs recursive file searches using glob patterns.
  3. `preview_file`: Safely previews a file by returning the first `N` lines and last `M` lines, avoiding token pollution.
  4. `project_overview`: Scans files up to depth 3, lists the 10 most recently modified files, and reads `README.md`.
  5. `upload_chunk`: Uploads base64-encoded file chunks for remote storage.
  6. `assemble_upload`: Assembles uploaded file chunks into a single file.
  7. `download_chunk`: Downloads a chunk of a remote file.
  8. `compress_archive`: Compresses a target directory into a `.zip`, `.tar.gz`, or `.tgz` archive.
  9. `extract_archive`: Extracts a `.zip` or `.tar.gz` archive to a target directory.

  ### Directory State
  10. `get_working_directory`: Returns the current active working directory (CWD).
  11. `change_working_directory`: Changes the active working directory (validates against allowed root).

  ### Background Jobs
  12. `start_background_job`: Spawns a command asynchronously in the background.
  13. `get_job_status`: Gets metadata, exit code, and run status of a job.
  14. `list_background_jobs`: Lists all background jobs sorted chronologically.
  15. `read_job_logs`: Previews logs for a specific background job.
  16. `kill_background_job`: Recursively kills a background job's process tree.
  ```

- [ ] **Step 2: Commit documentation update**
  ```bash
  git add README.md
  git commit -m "docs: rewrite README.md with comprehensive tools, config, and CLI guide"
  ```

---

### Task 3: Formatting & Linting

**Files:**
- Modify: All source files (formatting and lint checks)

**Interfaces:**
- Consumes: None
- Produces: Pristinely formatted codebase.

- [ ] **Step 1: Run ruff format**
  Run: `.venv\Scripts\ruff format .`
  Expected: Formats all python files.

- [ ] **Step 2: Run ruff check**
  Run: `.venv\Scripts\ruff check . --fix`
  Expected: Clean report or auto-fixes.

- [ ] **Step 3: Verify all tests still pass**
  Run: `.venv\Scripts\pytest`
  Expected: 38 passed.

- [ ] **Step 4: Commit any format/style adjustments**
  ```bash
  git commit -am "style: run ruff format and lint checks across codebase"
  ```

---

### Task 4: Add uvx and Agent Configuration Guide to README.md

**Files:**
- [MODIFY] [README.md](file:///C:/Users/abdo/.gemini/antigravity/scratch/gangway/README.md)

**Interfaces:**
- Consumes: None
- Produces: Enhanced installation and agent integration guide in README.md.

- [ ] **Step 1: Append uvx and Agent Setup details to `README.md`**
  Modify `README.md` to add `uvx` usage instructions and full configuration JSON examples for Claude Desktop and Cursor.
  Specifically, edit the "Installation" and "CLI Usage" sections to showcase running with `uvx` directly without installation, and add a "Claude Desktop & Cursor Configuration" section.

  Example content to add/merge:
  ```markdown
  ## Run with uvx (No Installation Required)

  You can run Gangway as an MCP server instantly without installing it globally using `uvx`:
  ```bash
  uvx gangway --transport stdio --token YOUR_SECRET_TOKEN --allowed-root /path/to/sandbox
  ```

  ## Register in AI Clients (Claude Desktop / Cursor)

  ### Claude Desktop
  Add the following to your `claude_desktop_config.json` (usually located at `%APPDATA%\Claude\claude_desktop_config.json` on Windows or `~/Library/Application Support/Claude/claude_desktop_config.json` on macOS):

  ```json
  {
    "mcpServers": {
      "gangway": {
        "command": "uvx",
        "args": [
          "gangway",
          "--transport", "stdio",
          "--token", "YOUR_SECRET_TOKEN",
          "--allowed-root", "/path/to/sandbox"
        ]
      }
    }
  }
  ```

  ### Cursor / VSCode
  1. Open Cursor Settings -> Features -> MCP.
  2. Click **+ Add New MCP Server**.
  3. Enter:
     * **Name**: `gangway`
     * **Type**: `command`
     * **Command**: `uvx gangway --transport stdio --token YOUR_SECRET_TOKEN --allowed-root /path/to/sandbox`
  ```

- [ ] **Step 2: Commit documentation update**
  ```bash
  git add README.md
  git commit -m "docs: add uvx and agent integration guides for Claude Desktop and Cursor to README.md"
  ```

## Verification Plan

### Automated Tests
- Running `.venv\Scripts\pytest` must return 38 passed tests with no failures.
- Running `.venv\Scripts\ruff check .` must return zero lint errors.
