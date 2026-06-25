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

### Run with uvx (No Installation Required)

You can run Gangway as an MCP server instantly without installing it globally using `uvx`:
```bash
uvx gangway --transport stdio --token YOUR_SECRET_TOKEN --allowed-root /path/to/sandbox
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
# If installed globally:
gangway --transport stdio --token secret-token --allowed-root /path/to/sandbox

# Or run instantly with uvx:
uvx gangway --transport stdio --token secret-token --allowed-root /path/to/sandbox
```

To run the server using `sse` transport:
```bash
# If installed globally:
gangway --transport sse --host 127.0.0.1 --port 8000 --token secret-token --allowed-root /path/to/sandbox

# Or run instantly with uvx:
uvx gangway --transport sse --host 127.0.0.1 --port 8000 --token secret-token --allowed-root /path/to/sandbox
```

Using a configuration file:
```bash
# If installed globally:
gangway --config /path/to/config.toml --transport sse

# Or run instantly with uvx:
uvx gangway --config /path/to/config.toml --transport sse
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
