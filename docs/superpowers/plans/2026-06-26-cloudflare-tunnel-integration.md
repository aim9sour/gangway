# Zero-Config Cloudflare Tunnel Integration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Integrate a Zero-Config Cloudflare Tunnel into Gangway. When starting the SSE transport server, if `--tunnel` is enabled, Gangway will locate (or automatically download) `cloudflared`, start it in the background, extract the public HTTPS URL, and output copy-pasteable JSON configuration blocks for Claude Desktop and Cursor.

**Architecture:** 
- Add `tunnel` configuration option to `Config` class and CLI parser.
- Create a `tunnel` manager module that downloads OS-specific `cloudflared` binaries to `~/.gangway/bin` if not found.
- Spawn `cloudflared` as a background process and parse its logs to print the trycloudflare URL and copy-pasteable client configuration blocks.
- Terminate the subprocess on exit.

**Tech Stack:** Python standard libraries (`urllib.request`, `subprocess`, `re`, `threading`, `atexit`, `json`), Uvicorn, Pytest.

## Global Constraints
- Project Root Directory: `C:\Users\abdo\.gemini\antigravity\scratch\gangway`
- Package Name: `gangway`
- Minimum dependencies: only standard libraries and already approved packages.
- Run lint checks using `ruff check` and formatting using `ruff format`.
- Verify all tests pass with `pytest`.

---

### Task 1: Configuration & CLI Updates

**Files:**
- [MODIFY] [config.py](file:///C:/Users/abdo/.gemini/antigravity/scratch/gangway/src/gangway/core/config.py)
- [MODIFY] [cli.py](file:///C:/Users/abdo/.gemini/antigravity/scratch/gangway/src/gangway/cli.py)
- [MODIFY] [test_config.py](file:///C:/Users/abdo/.gemini/antigravity/scratch/gangway/tests/test_config.py)
- [MODIFY] [test_cli.py](file:///C:/Users/abdo/.gemini/antigravity/scratch/gangway/tests/test_cli.py)

**Interfaces:**
- Consumes: None
- Produces: Updated `Config` class with `tunnel` attribute and CLI `--tunnel` parsing support.

- [ ] **Step 1: Write failing tests for Config & CLI tunnel option**
  - Add tests in `tests/test_config.py` asserting that `--tunnel` and `GANGWAY_TUNNEL=true` load `Config.tunnel = True`.
  - Add tests in `tests/test_cli.py` asserting that `--tunnel` parameter triggers SSE start with `cfg.tunnel = True`.

- [ ] **Step 2: Run tests to verify they fail**
  Run: `.venv\Scripts\pytest tests/test_config.py tests/test_cli.py`
  Expected: FAIL (AttributeError / ArgumentError)

- [ ] **Step 3: Update `src/gangway/core/config.py`**
  - Add `tunnel: bool = False` to `Config` class.
  - Parse `GANGWAY_TUNNEL` in `load_config`.
  - Parse `"tunnel"` from JSON/TOML configuration data.
  - Set `cfg.tunnel = tunnel` from CLI argument in `load_config`.

- [ ] **Step 4: Update `src/gangway/cli.py`**
  - Add `--tunnel` argument to CLI argparse:
    ```python
    parser.add_argument("--tunnel", action="store_true", help="Enable Zero-Config Cloudflare Tunnel for SSE transport")
    ```
  - Pass `tunnel=args.tunnel` to `load_config` call inside `main`.

- [ ] **Step 5: Run tests to verify they pass**
  Run: `.venv\Scripts\pytest tests/test_config.py tests/test_cli.py`
  Expected: PASS

- [ ] **Step 6: Commit changes**
  ```bash
  git add src/gangway/core/config.py src/gangway/cli.py tests/test_config.py tests/test_cli.py
  git commit -m "feat: add tunnel option to Config and CLI parser"
  ```

---

### Task 2: Implement Tunnel Manager Module

**Files:**
- [NEW] [tunnel.py](file:///C:/Users/abdo/.gemini/antigravity/scratch/gangway/src/gangway/core/tunnel.py)
- [NEW] [test_tunnel.py](file:///C:/Users/abdo/.gemini/antigravity/scratch/gangway/tests/test_tunnel.py)

**Interfaces:**
- Consumes: `Config`
- Produces:
  - `start_tunnel_background(port: int, token: Optional[str])`
  - `stop_tunnel()`

- [ ] **Step 1: Write mock tests for `tunnel.py`**
  Create `tests/test_tunnel.py` to mock `urllib.request.urlretrieve` (to prevent downloading during offline tests) and mock `subprocess.Popen` to verify that the tunnel starts and parses the regex trycloudflare URL correctly.

- [ ] **Step 2: Run tests to verify they fail**
  Run: `.venv\Scripts\pytest tests/test_tunnel.py`
  Expected: FAIL (ModuleNotFoundError)

- [ ] **Step 3: Implement `src/gangway/core/tunnel.py`**
  - Add `get_cloudflared_path() -> Optional[str]` to check PATH or download `cloudflared` to `~/.gangway/bin`.
  - Add `get_download_url() -> Optional[str]` to return target URL based on OS (Windows, Linux, macOS) and architecture.
  - Add `start_tunnel(port: int, token: Optional[str])` to spawn `cloudflared tunnel --url http://127.0.0.1:{port}`.
  - Implement regex log scanning to extract `https://*.trycloudflare.com` URL.
  - Implement `print_mcp_configs(public_url: str, token: Optional[str])` to log copy-pasteable JSON configuration for Claude Desktop and Cursor.
  - Add clean termination exit handler via `atexit`.

- [ ] **Step 4: Run tests to verify they pass**
  Run: `.venv\Scripts\pytest tests/test_tunnel.py`
  Expected: PASS

- [ ] **Step 5: Commit tunnel module**
  ```bash
  git add src/gangway/core/tunnel.py tests/test_tunnel.py
  git commit -m "feat: implement Zero-Config Cloudflare Tunnel manager with auto-download and configuration printer"
  ```

---

### Task 3: Integrate Tunnel in SSE Server Startup

**Files:**
- [MODIFY] [mcp.py](file:///C:/Users/abdo/.gemini/antigravity/scratch/gangway/src/gangway/server/mcp.py)
- [MODIFY] [test_mcp.py](file:///C:/Users/abdo/.gemini/antigravity/scratch/gangway/tests/test_mcp.py)

**Interfaces:**
- Consumes: `gangway.core.tunnel.start_tunnel_background`
- Produces: Integrated tunnel startup on SSE server initialization.

- [ ] **Step 1: Write tests in `test_mcp.py`**
  Assert that when `Config.tunnel = True` is passed to `start_sse_server`, it triggers `start_tunnel_background` (using unittest.mock).

- [ ] **Step 2: Run tests to verify they fail**
  Run: `.venv\Scripts\pytest tests/test_mcp.py`
  Expected: FAIL (mock assert failed / tunnel not called)

- [ ] **Step 3: Update `src/gangway/server/mcp.py`**
  Inside `start_sse_server(cfg: Config)`, check if `cfg.tunnel` is True:
  ```python
  if cfg.tunnel:
      from gangway.core.tunnel import start_tunnel_background
      start_tunnel_background(cfg.port, cfg.token)
  ```

- [ ] **Step 4: Run tests to verify they pass**
  Run: `.venv\Scripts\pytest tests/test_mcp.py`
  Expected: PASS

- [ ] **Step 5: Commit changes**
  ```bash
  git add src/gangway/server/mcp.py tests/test_mcp.py
  git commit -m "feat: integrate Cloudflare Tunnel in start_sse_server initialization"
  ```

## Verification Plan

### Automated Tests
- Running `.venv\Scripts\pytest` must return 100% pass rate across all tests (no failures, no syntax errors, and fully mocked network/processes).
- Running `ruff check .` must return zero errors.
