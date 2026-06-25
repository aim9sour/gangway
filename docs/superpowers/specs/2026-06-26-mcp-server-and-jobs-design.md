# Design Specification: MCP Server & Background Job Control

**Date**: 2026-06-26  
**Author**: Antigravity (AI Assistant)  
**Status**: Approved  
**Target Project**: `gangway`  

---

## 1. Goal & Context
The goal is to design and implement:
1. **Directory State Management**: Persistent tracking of the active working directory of the server.
2. **Background Job Control**: Spawning, tracking, and termination of asynchronous shell processes, with full metadata persistence and output logging.
3. **MCP Server**: A low-level Model Context Protocol (MCP) server wrapping all file, state, and job operations, offering both `stdio` and `sse` transports, protected by token authentication.
4. **CLI Entrypoint**: A simple command-line interface to start the server with the desired transport and configuration.

---

## 2. Technical Stack & Dependencies
* **Framework**: Core `mcp` library (v1.x decorator-based protocol).
* **ASGI Server & Framework**: `starlette` (routing & SSE connection management), `uvicorn` (ASGI execution runner).
* **Process Tracking**: `psutil` (for process tree reaping and status validation).
* **Build System**: `hatchling` / `uv`.

We will add the following to `pyproject.toml` dependencies:
* `mcp>=1.2.0`
* `starlette>=0.27.0`
* `uvicorn>=0.22.0`

---

## 3. Component Details & APIs

### 3.1 Directory & Path State Manager (`src/gangway/core/state.py`)
Maintains the active working directory.
* **State File**: `.gangway_state.json` inside the `allowed_root` or current working directory.
* **Atomic Write**: Modifies state by writing to a `.tmp` file and executing `os.replace` to prevent file corruption.
* **APIs**:
  * `get_cwd() -> str`
  * `set_cwd(path: str) -> str`: Resolves path relative to active CWD, verifies sandboxing bounds via `verify_path`, checks if it is a directory, and updates persistent state.
  * `resolve_path(path: str) -> str`: Converts a relative path to absolute against active CWD and verifies it against `allowed_root`.

### 3.2 Background Job Manager (`src/gangway/core/jobs.py`)
Spawns and monitors shell processes.
* **Job Directory**: `.gangway_jobs/` inside `allowed_root` or current working directory.
* **Per-Job Metadata**: `.gangway_jobs/<job_id>.json` contains job ID, command, PID, status (`running`, `success`, `failed`, `killed`), exit code, CWD, start/end timestamps. Updated atomically.
* **Per-Job Logs**: `.gangway_jobs/<job_id>.log` contains merged stdout/stderr.
* **APIs**:
  * `start_job(cmd: str, cwd: str) -> str`: Spawns process using `subprocess.Popen` in non-blocking mode.
  * `get_job_status(job_id: str) -> Dict[str, Any]`: Inspects process status using `psutil`. If process is dead, updates metadata.
  * `list_jobs() -> List[Dict[str, Any]]`: Scans job directory, re-validates and returns all job statuses sorted chronologically.
  * `kill_job(job_id: str) -> bool`: Terminates target process tree (parent and all sub-processes) using `psutil`.
  * `read_job_logs(job_id: str, head: int, tail: int) -> str`: Reads job's log using token-saving head/tail logic.

### 3.3 MCP Server (`src/gangway/server/mcp.py`)
Low-level `Server` configuration exposing all bridge tools.
* **Tools**:
  * `list_directory(path: Optional[str])`
  * `glob_search(pattern: str)`
  * `preview_file(path: str, head: int, tail: int)`
  * `project_overview(path: Optional[str])`
  * `upload_chunk(file_path: str, chunk_index: int, total_chunks: int, data_b64: str)`
  * `assemble_upload(file_path: str, total_chunks: int)`
  * `download_chunk(file_path: str, chunk_index: int, chunk_size: int)`
  * `compress_archive(archive_path: str, source_dir: str, format: str)`
  * `extract_archive(archive_path: str, extract_dir: str)`
  * `get_working_directory()`
  * `change_working_directory(path: str)`
  * `start_background_job(cmd: str, cwd: Optional[str])`
  * `get_job_status(job_id: str)`
  * `list_background_jobs()`
  * `read_job_logs(job_id: str, head: int, tail: int)`
  * `kill_background_job(job_id: str)`

* **Transports**:
  * **stdio**: Connects standard streams to the server runner using `mcp.server.stdio.stdio_server()`.
  * **SSE**: Exposes `/sse` (GET, returns event-stream) and `/messages/` (POST, forwards messages to the SSE transport). Protected by token checks against headers (`Authorization: Bearer <token>`) and query params (`?token=<token>`).

### 3.4 CLI entrypoint (`src/gangway/cli.py`)
Parses flags (`--config`, `--token`, `--allowed-root`, `--port`, `--host`, `--transport`) and launches the server.

---

## 4. Verification & Testing Plan
* **Automated Tests**:
  * Write `tests/test_state.py` to test state storage, relative resolution, directory changing, and sandboxing integration.
  * Write `tests/test_jobs.py` to test non-blocking job execution, metadata file output, log capturing, tree termination, and status recovery after simulated crashes.
  * Write `tests/test_mcp.py` to test JSON-RPC tool list, tool executions, SSE routing, and token authorization.
* **Manual Verification**:
  * Verify stdio transport with MCP Inspector: `npx @modelcontextprotocol/inspector`
  * Verify SSE transport and authentication endpoints via HTTP client or test scripts.
