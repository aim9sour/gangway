# MCP Server & Background Job Control Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement Directory State Management, Background Job Control with process tree termination, and an MCP Server supporting both `stdio` and `sse` transports with token authentication and CLI integration.

**Architecture:** Create a decoupled architecture with core managers for state and jobs, a low-level MCP server mapping tools to these managers, and a CLI entrypoint wrapper, built using the `mcp` core SDK, `starlette`, `uvicorn`, and `psutil`.

**Tech Stack:** Python, `mcp`, `starlette`, `uvicorn`, `psutil`, `pytest`, `uv`

## Global Constraints

- Project Root Directory: `C:\Users\abdo\.gemini\antigravity\scratch\gangway`
- Package Name: `gangway`
- Keep dependencies minimal; use standard library whenever possible.
- Implement atomic writes via temporary files and `os.replace` for all JSON states/metadata to prevent data corruption.
- Follow TDD (Red-Green-Refactor) with frequent Git commits.

---

### Task 1: Package Dependencies Setup

**Files:**
- Modify: `C:\Users\abdo\.gemini\antigravity\scratch\gangway\pyproject.toml`

**Interfaces:**
- Consumes: None
- Produces: Project dependencies updated for building/testing.

- [ ] **Step 1: Update dependencies in pyproject.toml**
  Open `pyproject.toml` and append `mcp>=1.2.0`, `starlette>=0.27.0`, and `uvicorn>=0.22.0` to the `dependencies` list:
  ```toml
  dependencies = [
      "tomli; python_version < '3.11'",
      "psutil>=5.9.0",
      "mcp>=1.2.0",
      "starlette>=0.27.0",
      "uvicorn>=0.22.0",
  ]
  ```

- [ ] **Step 2: Sync dependencies using uv**
  Run command in `C:\Users\abdo\.gemini\antigravity\scratch\gangway`:
  `uv sync`
  Expected: Installation completes successfully, updating `uv.lock`.

- [ ] **Step 3: Verify packages can be imported**
  Run: `uv run python -c "import mcp; import starlette; import uvicorn; import psutil; print('OK')"`
  Expected: Prints `OK` without errors.

- [ ] **Step 4: Commit**
  Run:
  ```bash
  git add pyproject.toml uv.lock
  git commit -m "chore: add mcp, starlette, and uvicorn dependencies"
  ```

---

### Task 2: Directory State Manager

**Files:**
- Create: `C:\Users\abdo\.gemini\antigravity\scratch\gangway\src\gangway\core\state.py`
- Create: `C:\Users\abdo\.gemini\antigravity\scratch\gangway\tests\test_state.py`

**Interfaces:**
- Consumes: `gangway.core.sandbox.verify_path`
- Produces:
  - `StateManager(allowed_root: Optional[str] = None, state_file_path: Optional[str] = None)`
  - `StateManager.get_cwd() -> str`
  - `StateManager.set_cwd(path: str) -> str`
  - `StateManager.resolve_path(path: str) -> str`

- [ ] **Step 1: Write the failing test**
  Create `tests/test_state.py`:
  ```python
  import os
  import json
  import tempfile
  import pytest
  from pathlib import Path
  from gangway.core.state import StateManager

  def test_state_manager_behavior():
      with tempfile.TemporaryDirectory() as tmpdir:
          allowed_root = Path(tmpdir).resolve()
          state_file = allowed_root / ".gangway_state.json"
          
          # Initialize
          sm = StateManager(allowed_root=str(allowed_root), state_file_path=str(state_file))
          assert Path(sm.get_cwd()) == allowed_root
          
          # Change directory (relative)
          sub_dir = allowed_root / "subdir"
          sub_dir.mkdir()
          sm.set_cwd("subdir")
          assert Path(sm.get_cwd()) == sub_dir
          
          # Verify state file persistence
          assert state_file.exists()
          with open(state_file, "r") as f:
              data = json.load(f)
              assert data["cwd"] == str(sub_dir)
              
          # Resolve path relative to current CWD
          res = sm.resolve_path("file.txt")
          assert Path(res) == sub_dir / "file.txt"
          
          # Sandboxing check outside allowed_root
          with pytest.raises(PermissionError):
              sm.set_cwd("../outside")
  ```

- [ ] **Step 2: Run test to verify it fails**
  Run: `uv run pytest tests/test_state.py`
  Expected: FAIL (ModuleNotFoundError)

- [ ] **Step 3: Write minimal implementation**
  Create `src/gangway/core/state.py`:
  ```python
  import os
  import json
  from pathlib import Path
  from typing import Optional
  from gangway.core.sandbox import verify_path

  class StateManager:
      def __init__(self, allowed_root: Optional[str] = None, state_file_path: Optional[str] = None):
          self.allowed_root = Path(allowed_root).resolve() if allowed_root else None
          
          if state_file_path:
              self.state_file = Path(state_file_path)
          elif self.allowed_root:
              self.state_file = self.allowed_root / ".gangway_state.json"
          else:
              self.state_file = Path(os.getcwd()) / ".gangway_state.json"
              
          self._current_cwd = self._load_state()

      def _load_state(self) -> Path:
          if self.state_file.exists():
              try:
                  with open(self.state_file, "r", encoding="utf-8") as f:
                      data = json.load(f)
                      saved_path = Path(data.get("cwd", ""))
                      if self.allowed_root:
                          verify_path(str(saved_path), str(self.allowed_root))
                      return saved_path.resolve()
              except Exception:
                  pass
          return self.allowed_root if self.allowed_root else Path(os.getcwd()).resolve()

      def _save_state(self):
          try:
              self.state_file.parent.mkdir(parents=True, exist_ok=True)
              temp_file = self.state_file.with_suffix(".tmp")
              with open(temp_file, "w", encoding="utf-8") as f:
                  json.dump({"cwd": str(self._current_cwd)}, f, indent=2)
              os.replace(temp_file, self.state_file)
          except Exception:
              try:
                  if temp_file.exists():
                      temp_file.unlink()
              except Exception:
                  pass

      def get_cwd(self) -> str:
          return str(self._current_cwd)

      def set_cwd(self, path_str: str) -> str:
          target_path = Path(path_str)
          if not target_path.is_absolute():
              target_path = self._current_cwd / target_path
              
          resolved_path = Path(verify_path(str(target_path), str(self.allowed_root) if self.allowed_root else None))
          
          if not resolved_path.is_dir():
              raise NotADirectoryError(f"'{path_str}' is not a directory")
              
          self._current_cwd = resolved_path
          self._save_state()
          return str(self._current_cwd)

      def resolve_path(self, path_str: str) -> str:
          target_path = Path(path_str)
          if not target_path.is_absolute():
              target_path = self._current_cwd / target_path
          return verify_path(str(target_path), str(self.allowed_root) if self.allowed_root else None)
  ```

- [ ] **Step 4: Run test to verify it passes**
  Run: `uv run pytest tests/test_state.py`
  Expected: PASS

- [ ] **Step 5: Commit**
  Run:
  ```bash
  git add src/gangway/core/state.py tests/test_state.py
  git commit -m "feat: implement Directory State Manager with atomic writes and sandboxing"
  ```

---

### Task 3: Background Job Manager

**Files:**
- Create: `C:\Users\abdo\.gemini\antigravity\scratch\gangway\src\gangway\core\jobs.py`
- Create: `C:\Users\abdo\.gemini\antigravity\scratch\gangway\tests\test_jobs.py`

**Interfaces:**
- Consumes: `gangway.core.files.preview_file`
- Produces:
  - `JobManager(allowed_root: Optional[str] = None, jobs_dir: Optional[str] = None)`
  - `JobManager.start_job(cmd: str, cwd: str) -> str`
  - `JobManager.get_job_status(job_id: str) -> Dict[str, Any]`
  - `JobManager.list_jobs() -> List[Dict[str, Any]]`
  - `JobManager.kill_job(job_id: str) -> bool`
  - `JobManager.read_job_logs(job_id: str, head: int = 100, tail: int = 100) -> str`

- [ ] **Step 1: Write the failing test**
  Create `tests/test_jobs.py`:
  ```python
  import os
  import time
  import tempfile
  import pytest
  from pathlib import Path
  from gangway.core.jobs import JobManager

  def test_job_manager_flow():
      with tempfile.TemporaryDirectory() as tmpdir:
          allowed_root = Path(tmpdir).resolve()
          jobs_dir = allowed_root / "jobs"
          
          jm = JobManager(allowed_root=str(allowed_root), jobs_dir=str(jobs_dir))
          
          # Start a job that writes to stdout and sleeps
          cmd = 'python -c "import time; print(\'hello from job\'); time.sleep(10)"'
          job_id = jm.start_job(cmd, str(allowed_root))
          assert job_id.startswith("job_")
          
          # Read status immediately (should be running)
          status = jm.get_job_status(job_id)
          assert status["status"] == "running"
          assert status["pid"] is not None
          
          # Wait a moment for output and check log
          time.sleep(1)
          logs = jm.read_job_logs(job_id, head=10, tail=10)
          assert "hello from job" in logs
          
          # Terminate job
          assert jm.kill_job(job_id) is True
          
          # Verify status updated
          status = jm.get_job_status(job_id)
          assert status["status"] == "killed"
  ```

- [ ] **Step 2: Run test to verify it fails**
  Run: `uv run pytest tests/test_jobs.py`
  Expected: FAIL (ModuleNotFoundError)

- [ ] **Step 3: Write minimal implementation**
  Create `src/gangway/core/jobs.py`:
  ```python
  import os
  import sys
  import json
  import time
  import subprocess
  from pathlib import Path
  from typing import Optional, List, Dict, Any
  import psutil

  class JobManager:
      def __init__(self, allowed_root: Optional[str] = None, jobs_dir: Optional[str] = None):
          self.allowed_root = Path(allowed_root).resolve() if allowed_root else None
          
          if jobs_dir:
              self.jobs_dir = Path(jobs_dir)
          elif self.allowed_root:
              self.jobs_dir = self.allowed_root / ".gangway_jobs"
          else:
              self.jobs_dir = Path(os.getcwd()) / ".gangway_jobs"
              
          self.jobs_dir.mkdir(parents=True, exist_ok=True)

      def _atomic_write_json(self, file_path: Path, data: Dict[str, Any]):
          temp_file = file_path.with_suffix(".tmp")
          try:
              with open(temp_file, "w", encoding="utf-8") as f:
                  json.dump(data, f, indent=2)
              os.replace(temp_file, file_path)
          except Exception as e:
              if temp_file.exists():
                  try:
                      temp_file.unlink()
                  except:
                      pass
              raise e

      def _generate_job_id(self) -> str:
          return f"job_{int(time.time() * 1000)}"

      def start_job(self, cmd: str, cwd: str) -> str:
          job_id = self._generate_job_id()
          log_file_path = self.jobs_dir / f"{job_id}.log"
          meta_file_path = self.jobs_dir / f"{job_id}.json"

          log_file = open(log_file_path, "wb")

          try:
              proc = subprocess.Popen(
                  cmd,
                  shell=True,
                  cwd=cwd,
                  stdout=log_file,
                  stderr=subprocess.STDOUT,
                  preexec_fn=None if sys.platform == "win32" else os.setsid
              )
          except Exception as e:
              log_file.close()
              meta = {
                  "job_id": job_id,
                  "cmd": cmd,
                  "pid": None,
                  "status": "failed",
                  "exit_code": -1,
                  "cwd": cwd,
                  "start_time": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                  "end_time": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                  "error": str(e)
              }
              self._atomic_write_json(meta_file_path, meta)
              return job_id

          log_file.close()

          meta = {
              "job_id": job_id,
              "cmd": cmd,
              "pid": proc.pid,
              "status": "running",
              "exit_code": None,
              "cwd": cwd,
              "start_time": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
              "end_time": None
          }
          self._atomic_write_json(meta_file_path, meta)
          return job_id

      def get_job_status(self, job_id: str) -> Dict[str, Any]:
          meta_file_path = self.jobs_dir / f"{job_id}.json"
          if not meta_file_path.exists():
              raise FileNotFoundError(f"Job '{job_id}' not found")

          with open(meta_file_path, "r", encoding="utf-8") as f:
              meta = json.load(f)

          if meta["status"] == "running":
              pid = meta["pid"]
              alive = False
              if pid is not None:
                  try:
                      p = psutil.Process(pid)
                      if p.is_running() and p.status() != psutil.STATUS_ZOMBIE:
                          alive = True
                  except (psutil.NoSuchProcess, psutil.AccessDenied):
                      pass

              if not alive:
                  exit_code = -1
                  if pid is not None:
                      try:
                          res = os.waitpid(pid, os.WNOHANG)
                          if res[0] != 0:
                              status_code = res[1]
                              exit_code = os.WEXITSTATUS(status_code) if os.WIFEXITED(status_code) else -1
                      except Exception:
                          pass

                  meta["status"] = "success" if exit_code == 0 else "failed"
                  meta["exit_code"] = exit_code
                  meta["end_time"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
                  self._atomic_write_json(meta_file_path, meta)

          return meta

      def list_jobs(self) -> List[Dict[str, Any]]:
          jobs = []
          for file in self.jobs_dir.glob("job_*.json"):
              job_id = file.stem
              try:
                  status = self.get_job_status(job_id)
                  jobs.append(status)
              except Exception:
                  pass
          jobs.sort(key=lambda x: x["start_time"])
          return jobs

      def kill_job(self, job_id: str) -> bool:
          meta = self.get_job_status(job_id)
          if meta["status"] != "running":
              return False

          pid = meta["pid"]
          if pid is not None:
              try:
                  parent = psutil.Process(pid)
                  for child in parent.children(recursive=True):
                      child.kill()
                  parent.kill()
              except (psutil.NoSuchProcess, psutil.AccessDenied):
                  pass

          meta["status"] = "killed"
          meta["exit_code"] = -9
          meta["end_time"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
          self._atomic_write_json(self.jobs_dir / f"{job_id}.json", meta)
          return True

      def read_job_logs(self, job_id: str, head: int = 100, tail: int = 100) -> str:
          log_file_path = self.jobs_dir / f"{job_id}.log"
          if not log_file_path.exists():
              return "[No logs found for this job]"

          from gangway.core.files import preview_file
          return preview_file(str(log_file_path), str(self.jobs_dir), head=head, tail=tail)
  ```

- [ ] **Step 4: Run test to verify it passes**
  Run: `uv run pytest tests/test_jobs.py`
  Expected: PASS

- [ ] **Step 5: Commit**
  Run:
  ```bash
  git add src/gangway/core/jobs.py tests/test_jobs.py
  git commit -m "feat: implement Background Job Manager with process tree termination and output log reading"
  ```

---

### Task 4: MCP Server & starlette app

**Files:**
- Create: `C:\Users\abdo\.gemini\antigravity\scratch\gangway\src\gangway\server\mcp.py`
- Create: `C:\Users\abdo\.gemini\antigravity\scratch\gangway\tests\test_mcp.py`

**Interfaces:**
- Consumes: `gangway.core.state.StateManager`, `gangway.core.jobs.JobManager`, `gangway.core.config.Config`
- Produces:
  - `start_stdio_server(cfg: Config)`
  - `start_sse_server(cfg: Config)`
  - `app` (Starlette application)

- [ ] **Step 1: Write the failing test**
  Create `tests/test_mcp.py`:
  ```python
  import pytest
  from starlette.testclient import TestClient
  from gangway.core.config import Config
  import gangway.server.mcp as mcp_server

  def test_mcp_sse_server_auth():
      # Create config with token
      cfg = Config(token="secret_key")
      mcp_server.config = cfg
      
      client = TestClient(mcp_server.app)
      
      # 1. Access SSE without token
      response = client.get("/sse")
      assert response.status_code == 401
      
      # 2. Access SSE with invalid token
      response = client.get("/sse?token=bad_key")
      assert response.status_code == 401
      
      # 3. Access messages POST without token
      response = client.post("/messages/")
      assert response.status_code == 401
  ```

- [ ] **Step 2: Run test to verify it fails**
  Run: `uv run pytest tests/test_mcp.py`
  Expected: FAIL (ModuleNotFoundError)

- [ ] **Step 3: Write minimal implementation**
  Create `src/gangway/server/mcp.py`:
  ```python
  import os
  import json
  import logging
  from typing import Optional
  from mcp.server.lowlevel.server import Server
  import mcp.types as types
  import mcp.server.stdio
  from mcp.server.sse import SseServerTransport

  from starlette.applications import Starlette
  from starlette.requests import Request
  from starlette.responses import JSONResponse, Response
  from starlette.exceptions import HTTPException

  from gangway.core.config import Config
  from gangway.core.state import StateManager
  from gangway.core.jobs import JobManager
  import gangway.core.files as files_core

  logging.basicConfig(level=logging.INFO)
  logger = logging.getLogger("gangway.mcp")

  server = Server("gangway", "0.1.0")

  state_manager: Optional[StateManager] = None
  job_manager: Optional[JobManager] = None
  config: Optional[Config] = None

  @server.list_tools()
  async def handle_list_tools():
      return [
          types.Tool(
              name="list_directory",
              description="List contents of a directory.",
              inputSchema={
                  "type": "object",
                  "properties": {
                      "path": {"type": "string", "default": "."}
                  }
              }
          ),
          types.Tool(
              name="glob_search",
              description="Search for files recursively using glob.",
              inputSchema={
                  "type": "object",
                  "properties": {
                      "pattern": {"type": "string"}
                  },
                  "required": ["pattern"]
              }
          ),
          types.Tool(
              name="preview_file",
              description="Preview a file.",
              inputSchema={
                  "type": "object",
                  "properties": {
                      "path": {"type": "string"},
                      "head": {"type": "integer", "default": 80},
                      "tail": {"type": "integer", "default": 40}
                  },
                  "required": ["path"]
              }
          ),
          types.Tool(
              name="project_overview",
              description="Overview of the repository.",
              inputSchema={
                  "type": "object",
                  "properties": {
                      "path": {"type": "string", "default": "."}
                  }
              }
          ),
          types.Tool(
              name="upload_chunk",
              description="Upload a base64 chunk.",
              inputSchema={
                  "type": "object",
                  "properties": {
                      "file_path": {"type": "string"},
                      "chunk_index": {"type": "integer"},
                      "total_chunks": {"type": "integer"},
                      "data_b64": {"type": "string"}
                  },
                  "required": ["file_path", "chunk_index", "total_chunks", "data_b64"]
              }
          ),
          types.Tool(
              name="assemble_upload",
              description="Assemble chunks.",
              inputSchema={
                  "type": "object",
                  "properties": {
                      "file_path": {"type": "string"},
                      "total_chunks": {"type": "integer"}
                  },
                  "required": ["file_path", "total_chunks"]
              }
          ),
          types.Tool(
              name="download_chunk",
              description="Download chunk.",
              inputSchema={
                  "type": "object",
                  "properties": {
                      "file_path": {"type": "string"},
                      "chunk_index": {"type": "integer"},
                      "chunk_size": {"type": "integer", "default": 65536}
                  },
                  "required": ["file_path", "chunk_index"]
              }
          ),
          types.Tool(
              name="compress_archive",
              description="Compress directory.",
              inputSchema={
                  "type": "object",
                  "properties": {
                      "archive_path": {"type": "string"},
                      "source_dir": {"type": "string"},
                      "format": {"type": "string", "enum": ["zip", "tar.gz"], "default": "zip"}
                  },
                  "required": ["archive_path", "source_dir"]
              }
          ),
          types.Tool(
              name="extract_archive",
              description="Extract archive.",
              inputSchema={
                  "type": "object",
                  "properties": {
                      "archive_path": {"type": "string"},
                      "extract_dir": {"type": "string"}
                  },
                  "required": ["archive_path", "extract_dir"]
              }
          ),
          types.Tool(
              name="get_working_directory",
              description="Get active working directory.",
              inputSchema={"type": "object", "properties": {}}
          ),
          types.Tool(
              name="change_working_directory",
              description="Change active working directory.",
              inputSchema={
                  "type": "object",
                  "properties": {
                      "path": {"type": "string"}
                  },
                  "required": ["path"]
              }
          ),
          types.Tool(
              name="start_background_job",
              description="Start a background job.",
              inputSchema={
                  "type": "object",
                  "properties": {
                      "cmd": {"type": "string"},
                      "cwd": {"type": "string"}
                  },
                  "required": ["cmd"]
              }
          ),
          types.Tool(
              name="get_job_status",
              description="Get job status.",
              inputSchema={
                  "type": "object",
                  "properties": {
                      "job_id": {"type": "string"}
                  },
                  "required": ["job_id"]
              }
          ),
          types.Tool(
              name="list_background_jobs",
              description="List background jobs.",
              inputSchema={"type": "object", "properties": {}}
          ),
          types.Tool(
              name="read_job_logs",
              description="Read job logs.",
              inputSchema={
                  "type": "object",
                  "properties": {
                      "job_id": {"type": "string"},
                      "head": {"type": "integer", "default": 100},
                      "tail": {"type": "integer", "default": 100}
                  },
                  "required": ["job_id"]
              }
          ),
          types.Tool(
              name="kill_background_job",
              description="Kill a job.",
              inputSchema={
                  "type": "object",
                  "properties": {
                      "job_id": {"type": "string"}
                  },
                  "required": ["job_id"]
              }
          )
      ]

  @server.call_tool()
  async def handle_call_tool(name: str, arguments: dict):
      try:
          if name == "list_directory":
              raw_path = arguments.get("path", ".")
              resolved = state_manager.resolve_path(raw_path)
              res = files_core.list_directory(resolved, config.allowed_root)
              return types.CallToolResult(content=[types.TextContent(type="text", text=json.dumps(res, indent=2))])

          elif name == "glob_search":
              pattern = arguments["pattern"]
              res = files_core.glob_search(pattern, config.allowed_root)
              return types.CallToolResult(content=[types.TextContent(type="text", text=json.dumps(res, indent=2))])

          elif name == "preview_file":
              raw_path = arguments["path"]
              resolved = state_manager.resolve_path(raw_path)
              head = arguments.get("head", 80)
              tail = arguments.get("tail", 40)
              res = files_core.preview_file(resolved, config.allowed_root, head=head, tail=tail)
              return types.CallToolResult(content=[types.TextContent(type="text", text=res)])

          elif name == "project_overview":
              raw_path = arguments.get("path", ".")
              resolved = state_manager.resolve_path(raw_path)
              res = files_core.project_overview(resolved, config.allowed_root)
              return types.CallToolResult(content=[types.TextContent(type="text", text=json.dumps(res, indent=2))])

          elif name == "upload_chunk":
              raw_path = arguments["file_path"]
              resolved = state_manager.resolve_path(raw_path)
              chunk_idx = arguments["chunk_index"]
              total_chunks = arguments["total_chunks"]
              data_b64 = arguments["data_b64"]
              res = files_core.upload_chunk(resolved, chunk_idx, total_chunks, data_b64, config.allowed_root)
              return types.CallToolResult(content=[types.TextContent(type="text", text=str(res))])

          elif name == "assemble_upload":
              raw_path = arguments["file_path"]
              resolved = state_manager.resolve_path(raw_path)
              total_chunks = arguments["total_chunks"]
              res = files_core.assemble_upload(resolved, total_chunks, config.allowed_root)
              return types.CallToolResult(content=[types.TextContent(type="text", text=f"Assembled at: {res}")])

          elif name == "download_chunk":
              raw_path = arguments["file_path"]
              resolved = state_manager.resolve_path(raw_path)
              chunk_idx = arguments["chunk_index"]
              chunk_size = arguments.get("chunk_size", 65536)
              res = files_core.download_chunk(resolved, chunk_idx, chunk_size, config.allowed_root)
              return types.CallToolResult(content=[types.TextContent(type="text", text=json.dumps(res))])

          elif name == "compress_archive":
              archive_path = arguments["archive_path"]
              resolved_archive = state_manager.resolve_path(archive_path)
              source_dir = arguments["source_dir"]
              resolved_source = state_manager.resolve_path(source_dir)
              fmt = arguments.get("format", "zip")
              res = files_core.compress_archive(resolved_archive, resolved_source, config.allowed_root, format=fmt)
              return types.CallToolResult(content=[types.TextContent(type="text", text=f"Archive created at: {res}")])

          elif name == "extract_archive":
              archive_path = arguments["archive_path"]
              resolved_archive = state_manager.resolve_path(archive_path)
              extract_dir = arguments["extract_dir"]
              resolved_extract = state_manager.resolve_path(extract_dir)
              res = files_core.extract_archive(resolved_archive, resolved_extract, config.allowed_root)
              return types.CallToolResult(content=[types.TextContent(type="text", text=f"Extracted to: {res}")])

          elif name == "get_working_directory":
              return types.CallToolResult(content=[types.TextContent(type="text", text=state_manager.get_cwd())])

          elif name == "change_working_directory":
              path = arguments["path"]
              new_cwd = state_manager.set_cwd(path)
              return types.CallToolResult(content=[types.TextContent(type="text", text=f"Working directory changed to: {new_cwd}")])

          elif name == "start_background_job":
              cmd = arguments["cmd"]
              raw_cwd = arguments.get("cwd", state_manager.get_cwd())
              resolved_cwd = state_manager.resolve_path(raw_cwd)
              job_id = job_manager.start_job(cmd, resolved_cwd)
              return types.CallToolResult(content=[types.TextContent(type="text", text=job_id)])

          elif name == "get_job_status":
              job_id = arguments["job_id"]
              status = job_manager.get_job_status(job_id)
              return types.CallToolResult(content=[types.TextContent(type="text", text=json.dumps(status, indent=2))])

          elif name == "list_background_jobs":
              jobs_list = job_manager.list_jobs()
              return types.CallToolResult(content=[types.TextContent(type="text", text=json.dumps(jobs_list, indent=2))])

          elif name == "read_job_logs":
              job_id = arguments["job_id"]
              head = arguments.get("head", 100)
              tail = arguments.get("tail", 100)
              logs = job_manager.read_job_logs(job_id, head=head, tail=tail)
              return types.CallToolResult(content=[types.TextContent(type="text", text=logs)])

          elif name == "kill_background_job":
              job_id = arguments["job_id"]
              success = job_manager.kill_job(job_id)
              return types.CallToolResult(content=[types.TextContent(type="text", text="Job terminated successfully" if success else "Job is not running")])

          else:
              raise ValueError(f"Unknown tool: {name}")

      except Exception as e:
          logger.error(f"Error calling tool {name}: {e}", exc_info=True)
          return types.CallToolResult(
              content=[types.TextContent(type="text", text=f"Error executing {name}: {str(e)}")],
              isError=True
          )

  sse = SseServerTransport("/messages/")
  app = Starlette()

  def verify_token(request: Request):
      if not config or not config.token:
          return
      token = request.headers.get("Authorization")
      if token and token.startswith("Bearer "):
          token = token[7:]
      else:
          token = request.query_params.get("token")
      if token != config.token:
          raise HTTPException(status_code=401, detail="Unauthorized")

  @app.route("/sse", methods=["GET"])
  async def handle_sse(request: Request):
      verify_token(request)
      async def run_mcp_session():
          async with sse.connect_sse(request.scope, request.receive, request._send) as (read_stream, write_stream):
              await server.run(read_stream, write_stream, server.create_initialization_options())
      import asyncio
      asyncio.create_task(run_mcp_session())
      return Response(media_type="text/event-stream")

  @app.route("/messages/", methods=["POST"])
  async def handle_messages_post(request: Request):
      verify_token(request)
      return await sse.handle_post_message(request)

  def start_sse_server(cfg: Config):
      global config, state_manager, job_manager
      config = cfg
      state_manager = StateManager(allowed_root=cfg.allowed_root)
      job_manager = JobManager(allowed_root=cfg.allowed_root)
      import uvicorn
      logger.info(f"Starting MCP SSE server on {cfg.host}:{cfg.port}")
      uvicorn.run(app, host=cfg.host, port=cfg.port)

  def start_stdio_server(cfg: Config):
      global config, state_manager, job_manager
      config = cfg
      state_manager = StateManager(allowed_root=cfg.allowed_root)
      job_manager = JobManager(allowed_root=cfg.allowed_root)
      import anyio
      async def run_stdio():
          async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
              await server.run(read_stream, write_stream, server.create_initialization_options())
      logger.info("Starting MCP stdio server")
      anyio.run(run_stdio)
  ```

- [ ] **Step 4: Run test to verify it passes**
  Run: `uv run pytest tests/test_mcp.py`
  Expected: PASS

- [ ] **Step 5: Commit**
  Run:
  ```bash
  git add src/gangway/server/mcp.py tests/test_mcp.py
  git commit -m "feat: implement low-level MCP server and endpoints in starlette with token validation"
  ```

---

### Task 5: CLI Entrypoint

**Files:**
- Create: `C:\Users\abdo\.gemini\antigravity\scratch\gangway\src\gangway\cli.py`
- Create: `C:\Users\abdo\.gemini\antigravity\scratch\gangway\tests\test_cli.py`

**Interfaces:**
- Consumes: `gangway.server.mcp.start_stdio_server`, `gangway.server.mcp.start_sse_server`
- Produces: Command Line Interface parsing and launch hook.

- [ ] **Step 1: Write the failing test**
  Create `tests/test_cli.py`:
  ```python
  import sys
  import pytest
  from unittest.mock import patch
  from gangway.cli import main

  def test_cli_parsing():
      test_args = [
          "cli.py",
          "--token", "secret",
          "--allowed-root", "/tmp",
          "--transport", "stdio"
      ]
      with patch.object(sys, 'argv', test_args):
          with patch('gangway.cli.start_stdio_server') as mock_stdio:
              main()
              mock_stdio.assert_called_once()
              cfg = mock_stdio.call_args[0][0]
              assert cfg.token == "secret"
  ```

- [ ] **Step 2: Run test to verify it fails**
  Run: `uv run pytest tests/test_cli.py`
  Expected: FAIL (ModuleNotFoundError)

- [ ] **Step 3: Write minimal implementation**
  Create `src/gangway/cli.py`:
  ```python
  import argparse
  import sys
  from gangway.core.config import load_config
  from gangway.server.mcp import start_stdio_server, start_sse_server

  def main():
      parser = argparse.ArgumentParser(description="Gangway - The smart Agent-to-Server Bridge")
      parser.add_argument("--config", help="Path to config file (JSON/TOML)")
      parser.add_argument("--token", help="Bearer token for authentication")
      parser.add_argument("--allowed-root", help="Limit filesystem actions under this directory")
      parser.add_argument("--port", type=int, help="Port to run SSE server on")
      parser.add_argument("--host", help="Host to bind SSE server to")
      parser.add_argument("--transport", choices=["stdio", "sse"], default="stdio", help="Transport mechanism")

      args = parser.parse_args()

      try:
          cfg = load_config(
              config_file=args.config,
              token=args.token,
              allowed_root=args.allowed_root,
              port=args.port,
              host=args.host
          )
      except Exception as e:
          print(f"Error loading configuration: {e}", file=sys.stderr)
          sys.exit(1)

      if args.transport == "sse":
          start_sse_server(cfg)
      else:
          start_stdio_server(cfg)

  if __name__ == "__main__":
      main()
  ```

- [ ] **Step 4: Run test to verify it passes**
  Run: `uv run pytest tests/test_cli.py`
  Expected: PASS

- [ ] **Step 5: Commit**
  Run:
  ```bash
  git add src/gangway/cli.py tests/test_cli.py
  git commit -m "feat: implement CLI entrypoint for stdio and sse transport modes"
  ```
