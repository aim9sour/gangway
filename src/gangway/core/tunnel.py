import os
import platform
import shutil
import urllib.request
import subprocess
import re
import time
import atexit
import threading
import json
from pathlib import Path
from typing import Optional

_tunnel_process: Optional[subprocess.Popen] = None


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


def get_cloudflared_path() -> Optional[str]:
    # 1. Check system PATH first
    path_in_env = shutil.which("cloudflared")
    if path_in_env:
        print(f"Found cloudflared in PATH: {path_in_env}")
        return path_in_env

    # 2. Check local gangway bin directory
    bin_dir = Path.home() / ".gangway" / "bin"
    exe_name = "cloudflared.exe" if platform.system() == "Windows" else "cloudflared"
    local_path = bin_dir / exe_name

    if local_path.exists():
        print(f"Found cloudflared in local directory: {local_path}")
        return str(local_path)

    # 3. Download if not found
    url = get_download_url()
    if not url:
        print(
            "Could not determine appropriate cloudflared download URL for this platform/architecture."
        )
        return None

    os.makedirs(bin_dir, exist_ok=True)

    is_tgz = url.endswith(".tgz") or url.endswith(".tar.gz")
    tmp_path = bin_dir / (f"{exe_name}.tgz" if is_tgz else f"{exe_name}.tmp")
    print(f"Downloading cloudflared from {url} to {tmp_path}...")

    try:
        urllib.request.urlretrieve(url, str(tmp_path))
        print("Download complete.")

        if is_tgz:
            import tarfile

            print(f"Extracting {tmp_path}...")
            with tarfile.open(tmp_path, "r:gz") as tar:
                member = tar.getmember("cloudflared")
                tar.extract(member, path=str(bin_dir))
            try:
                os.remove(tmp_path)
            except Exception as remove_err:
                print(f"Error removing temporary archive: {remove_err}")
        else:
            os.replace(tmp_path, local_path)

        if platform.system() != "Windows":
            print(f"Setting executable permissions on {local_path}...")
            os.chmod(local_path, 0o755)

        return str(local_path)
    except Exception as e:
        print(f"Error downloading/extracting cloudflared: {e}")
        if tmp_path.exists():
            try:
                os.remove(tmp_path)
            except Exception as remove_err:
                print(f"Error removing temporary file: {remove_err}")
        return None


def print_mcp_configs(public_url: str, token: Optional[str], host: str = "127.0.0.1"):
    # Add token query param if present
    sse_url = f"{public_url}/sse"
    if token:
        sse_url += f"?token={token}"

    print("\n" + "=" * 80)
    print(" GANGWAY CLOUDFLARE TUNNEL IS RUNNING ".center(80, "="))
    print("=" * 80)
    print(f"Public Tunnel URL: {public_url}")
    print(f"SSE Endpoint:      {sse_url}")
    print("=" * 80)
    print("\n--- Cursor / VSCode MCP Config ---")
    print("1. Open Cursor Settings -> Features -> MCP")
    print("2. Click '+ Add New MCP Server'")
    print("3. Enter:")
    print("   - Name: gangway")
    print("   - Type: SSE")
    print(f"   - URL:  {sse_url}")
    # Correct path depending on platform
    sys_name = platform.system()
    if sys_name == "Darwin":
        config_path = "~/Library/Application Support/Claude/claude_desktop_config.json"
    elif sys_name == "Windows":
        config_path = "%APPDATA%\\Claude\\claude_desktop_config.json"
    else:
        config_path = "~/.config/Claude/claude_desktop_config.json"

    print(f"\n--- Claude Desktop Config ({config_path}) ---")

    claude_config = {
        "mcpServers": {
            "gangway": {
                "command": "npx",
                "args": [
                    "-y",
                    "@modelcontextprotocol/inspector",
                    sse_url,
                ],
            }
        }
    }

    print(json.dumps(claude_config, indent=2))
    print("=" * 80 + "\n")


def start_tunnel_background(
    port: int,
    token: Optional[str] = None,
    timeout: float = 15.0,
    host: str = "127.0.0.1",
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

    _tunnel_process = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    # Thread-safe state for communicating results from the background thread
    lock = threading.Lock()
    state = {
        "public_url": None,
        "startup_logs": [],
        "url_found": False,
    }

    url_pattern = re.compile(r"https://[a-zA-Z0-9-]+\.trycloudflare\.com")

    def reader_thread(stream):
        for line_bytes in iter(stream.readline, b""):
            line_str = line_bytes.decode("utf-8", errors="replace")
            print(f"[cloudflared] {line_str.strip()}", flush=True)

            with lock:
                url_found = state["url_found"]
                if not url_found:
                    state["startup_logs"].append(line_str)
                    match = url_pattern.search(line_str)
                    if match:
                        state["public_url"] = match.group(0)
                        state["url_found"] = True
        stream.close()

    t = threading.Thread(
        target=reader_thread, args=(_tunnel_process.stderr,), daemon=True
    )
    t.start()

    # Also consume stdout to avoid buffer filling up
    def stdout_drainer(stream):
        for _ in stream:
            pass
        stream.close()

    t_out = threading.Thread(
        target=stdout_drainer, args=(_tunnel_process.stdout,), daemon=True
    )
    t_out.start()

    start_time = time.time()
    public_url: Optional[str] = None

    while time.time() - start_time < timeout:
        # Check if process died
        if _tunnel_process.poll() is not None:
            # Let thread finish reading any final stderr lines
            t.join(timeout=1.0)
            with lock:
                err_msg = "".join(state["startup_logs"])
            raise RuntimeError(
                f"cloudflared process terminated unexpectedly. Logs:\n{err_msg}"
            )

        with lock:
            if state["url_found"]:
                public_url = state["public_url"]
                break

        time.sleep(0.1)

    if not public_url:
        stop_tunnel()
        raise RuntimeError("Timeout waiting for Cloudflare tunnel URL")

    print_mcp_configs(public_url, token, host=host)

    return public_url


def stop_tunnel():
    global _tunnel_process
    if _tunnel_process is not None:
        print("Stopping cloudflared tunnel...")
        try:
            _tunnel_process.terminate()
            try:
                _tunnel_process.wait(timeout=5.0)
            except subprocess.TimeoutExpired:
                print("cloudflared did not terminate in 5s. Killing...")
                _tunnel_process.kill()
                _tunnel_process.wait()
        except Exception as e:
            print(f"Error stopping cloudflared tunnel: {e}")
        finally:
            _tunnel_process = None
            print("cloudflared tunnel stopped.")


atexit.register(stop_tunnel)
