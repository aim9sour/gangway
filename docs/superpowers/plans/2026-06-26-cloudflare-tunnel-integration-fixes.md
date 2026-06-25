# Cloudflare Tunnel Integration Fixes Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Apply final code-review fixes for Cloudflare Tunnel integration, supporting macOS .tgz download/extraction, Windows ARM64 emulation fallback, and host/proxy mapping configurability.

**Architecture:** We will modify `src/gangway/core/tunnel.py` to update architecture mappings, handle `.tgz` archive extraction, and parse host options. We will update `src/gangway/server/mcp.py` to pass down the host setting, add unit tests in `tests/test_tunnel.py`, and run Ruff formatting/lint checks.

**Tech Stack:** Python, pytest.

## Global Constraints

- Update Darwin mapping in `get_download_url()` to support both `arm64` and `amd64` and point to `.tgz` releases.
- In `get_cloudflared_path()`, extract `cloudflared` from `.tgz` using `tarfile` and clean up.
- In Windows ARM64, fall back to downloading `amd64.exe`.
- Pass `host` (default `"127.0.0.1"`) through `start_tunnel_background` and `print_mcp_configs`. If `host` is `"0.0.0.0"`, target local proxy IP is `"127.0.0.1"`.
- Run `ruff format .` and `ruff check --fix .`.
- Ensure all tests pass.

---

### Task 1: Tunnel Code Updates (URL, Extraction, Host Configuration)

**Files:**
- Modify: `src/gangway/core/tunnel.py`

**Interfaces:**
- Consumes: None
- Produces: `get_download_url()`, `get_cloudflared_path()`, `start_tunnel_background(port, token=None, host="127.0.0.1")`, `print_mcp_configs(public_url, token, host="127.0.0.1")`

- [ ] **Step 1: Modify `get_download_url` in `src/gangway/core/tunnel.py`**

Add Windows arm64 fallback and Darwin arm64/amd64/x86_64 `.tgz` URL mappings.

```python
def get_download_url() -> Optional[str]:
    sys_name = platform.system()
    machine = platform.machine().lower()

    if sys_name == "Windows":
        if machine in ("amd64", "x86_64", "arm64"):
            return "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-windows-amd64.exe"
        elif machine in ("386", "i386", "i686"):
            return "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-windows-386.exe"
    elif sys_name == "Linux":
        if machine in ("amd64", "x86_64"):
            return "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64"
        elif machine in ("arm64", "aarch64"):
            return "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-arm64"
    elif sys_name == "Darwin":
        if machine in ("arm64", "aarch64"):
            return "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-darwin-arm64.tgz"
        elif machine in ("amd64", "x86_64"):
            return "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-darwin-amd64.tgz"
    return None
```

- [ ] **Step 2: Modify `get_cloudflared_path` in `src/gangway/core/tunnel.py`**

Handle `.tgz` files by extracting the `cloudflared` binary into the `bin_dir` and cleaning up the temp archive.

```python
    # 3. Download if not found
    url = get_download_url()
    if not url:
        print(
            "Could not determine appropriate cloudflared download URL for this platform/architecture."
        )
        return None

    os.makedirs(bin_dir, exist_ok=True)
    
    # Determine the temp filename based on whether URL points to tgz
    is_tgz = url.endswith(".tgz") or url.endswith(".tar.gz")
    tmp_ext = ".tgz" if is_tgz else ".tmp"
    tmp_path = bin_dir / f"{exe_name}{tmp_ext}"
    
    print(f"Downloading cloudflared from {url} to {tmp_path}...")

    try:
        urllib.request.urlretrieve(url, str(tmp_path))
        print("Download complete.")

        if is_tgz:
            import tarfile
            print(f"Extracting {tmp_path}...")
            with tarfile.open(tmp_path, "r:gz") as tar:
                # Extract 'cloudflared' member to local_path
                member = tar.getmember("cloudflared")
                # We extract it to bin_dir and it will be named 'cloudflared'
                tar.extract(member, path=str(bin_dir))
            
            # Clean up temp tgz file
            try:
                os.remove(tmp_path)
            except Exception as e:
                print(f"Error removing temporary archive: {e}")
        else:
            # Chmod on Unix platforms before replacing
            if platform.system() != "Windows":
                print(f"Setting executable permissions on {tmp_path}...")
                os.chmod(tmp_path, 0o755)
            os.replace(tmp_path, local_path)

        # Ensure executable permissions on local_path for Unix
        if platform.system() != "Windows":
            print(f"Setting executable permissions on {local_path}...")
            os.chmod(local_path, 0o755)

        return str(local_path)
```

- [ ] **Step 3: Update `print_mcp_configs` in `src/gangway/core/tunnel.py`**

Add `host` parameter (default `"127.0.0.1"`) and update calls.

```python
def print_mcp_configs(public_url: str, token: Optional[str], host: str = "127.0.0.1"):
```

- [ ] **Step 4: Update `start_tunnel_background` in `src/gangway/core/tunnel.py`**

Add `host` parameter (default `"127.0.0.1"`). Use `"127.0.0.1"` if `host` is `"0.0.0.0"`.

```python
def start_tunnel_background(
    port: int, token: Optional[str] = None, timeout: float = 15.0, host: str = "127.0.0.1"
) -> str:
    global _tunnel_process

    if _tunnel_process is not None:
        stop_tunnel()

    cf_path = get_cloudflared_path()
    if not cf_path:
        raise RuntimeError(
            "cloudflared executable not found and could not be downloaded"
        )

    target_host = "127.0.0.1" if host == "0.0.0.0" else host
    cmd = [cf_path, "tunnel", "--url", f"http://{target_host}:{port}"]
    print(f"Starting cloudflared tunnel command: {' '.join(cmd)}")
    
    # ...
    
    # Near end of start_tunnel_background:
    print_mcp_configs(public_url, token, host=host)

    return public_url
```

---

### Task 2: Server Updates (Passing Host Configuration)

**Files:**
- Modify: `src/gangway/server/mcp.py`

**Interfaces:**
- Consumes: `cfg.host`
- Produces: Correct invocation of `start_tunnel_background`

- [ ] **Step 1: Modify `start_sse_server` in `src/gangway/server/mcp.py`**

Pass `cfg.host` down to `start_tunnel_background`:

```python
    if cfg.tunnel:
        from gangway.core.tunnel import start_tunnel_background
        start_tunnel_background(cfg.port, cfg.token, host=cfg.host)
```

---

### Task 3: Unit Tests and Mock Updates

**Files:**
- Modify: `tests/test_tunnel.py`
- Modify: `tests/test_mcp.py`

- [ ] **Step 1: Modify `tests/test_mcp.py` to match new `start_tunnel_background` signature**

Update `test_start_sse_server_with_tunnel` mock assertions:
```python
            # Verify start_tunnel_background was called
            mock_start_tunnel.assert_called_once_with(cfg.port, cfg.token, host=cfg.host)
```

- [ ] **Step 2: Add test case for Darwin .tgz extraction in `tests/test_tunnel.py`**

```python
def test_get_cloudflared_path_download_darwin_tgz():
    # Verify downloading and extracting a tgz file for Darwin arm64 works
    with (
        patch("shutil.which", return_value=None),
        patch("pathlib.Path.home", return_value=Path("/home/user")),
        patch("os.makedirs") as mock_makedirs,
        patch("urllib.request.urlretrieve") as mock_urlretrieve,
        patch("os.chmod") as mock_chmod,
        patch("platform.system", return_value="Darwin"),
        patch("platform.machine", return_value="arm64"),
        # Mock Path.exists to return False so we run the download flow
        patch.object(Path, "exists", return_value=False),
        patch("tarfile.open") as mock_tar_open,
        patch("os.remove") as mock_remove,
    ):
        # Set up tarfile mock
        mock_tar = MagicMock()
        mock_member = MagicMock()
        mock_tar.getmember.return_value = mock_member
        mock_tar_open.return_value.__enter__.return_value = mock_tar

        path = get_cloudflared_path()
        assert path == str(Path("/home/user/.gangway/bin/cloudflared"))

        # Verify urlretrieve was called with the correct Darwin arm64 url
        mock_urlretrieve.assert_called_once()
        url = mock_urlretrieve.call_args[0][0]
        assert url == "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-darwin-arm64.tgz"

        # Verify tarfile open and extraction
        mock_tar_open.assert_called_once()
        open_args = mock_tar_open.call_args[0]
        assert str(open_args[0]).endswith("cloudflared.tgz")
        assert open_args[1] == "r:gz"

        mock_tar.getmember.assert_called_once_with("cloudflared")
        mock_tar.extract.assert_called_once_with(mock_member, path=str(Path("/home/user/.gangway/bin")))

        # Verify temp tgz file removal
        mock_remove.assert_called_once()
        assert str(mock_remove.call_args[0][0]).endswith("cloudflared.tgz")

        # Verify executable chmod on the final bin path
        mock_chmod.assert_called_once()
        assert mock_chmod.call_args[0][0] == Path("/home/user/.gangway/bin/cloudflared")
        assert mock_chmod.call_args[0][1] == 0o755
```

- [ ] **Step 3: Run pytest to verify all tests pass**

Run `uv run pytest`.

---

### Task 4: Linting & Commit

- [ ] **Step 1: Format and lint code**

Run:
```bash
uv run ruff format .
uv run ruff check --fix .
```

- [ ] **Step 2: Commit changes**

Commit:
```bash
git add src/gangway/core/tunnel.py src/gangway/server/mcp.py tests/test_tunnel.py tests/test_mcp.py
git commit -m "fix: apply final code review fixes for Cloudflare Tunnel integration"
```

- [ ] **Step 3: Update report**

Modify: `C:\Users\abdo\.gemini\antigravity\scratch\gangway\.superpowers\sdd\task-3-report.md`
