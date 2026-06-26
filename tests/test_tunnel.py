from pathlib import Path
from unittest.mock import patch, MagicMock
import pytest

from gangway.core.tunnel import (
    get_download_url,
    get_cloudflared_path,
    start_tunnel_background,
    stop_tunnel,
)


def test_get_download_url():
    # 1. Windows amd64
    with (
        patch("platform.system", return_value="Windows"),
        patch("platform.machine", return_value="AMD64"),
    ):
        url = get_download_url()
        assert (
            url
            == "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-windows-amd64.exe"
        )

    # Windows arm64 fallback
    with (
        patch("platform.system", return_value="Windows"),
        patch("platform.machine", return_value="arm64"),
    ):
        url = get_download_url()
        assert (
            url
            == "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-windows-amd64.exe"
        )

    # 2. Windows 386
    with (
        patch("platform.system", return_value="Windows"),
        patch("platform.machine", return_value="i386"),
    ):
        url = get_download_url()
        assert (
            url
            == "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-windows-386.exe"
        )

    # 3. Linux amd64
    with (
        patch("platform.system", return_value="Linux"),
        patch("platform.machine", return_value="x86_64"),
    ):
        url = get_download_url()
        assert (
            url
            == "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64"
        )

    # 4. Linux arm64
    with (
        patch("platform.system", return_value="Linux"),
        patch("platform.machine", return_value="aarch64"),
    ):
        url = get_download_url()
        assert (
            url
            == "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-arm64"
        )

    # 5. Darwin (macOS) amd64/arm64
    with (
        patch("platform.system", return_value="Darwin"),
        patch("platform.machine", return_value="x86_64"),
    ):
        url = get_download_url()
        assert (
            url
            == "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-darwin-amd64.tgz"
        )

    with (
        patch("platform.system", return_value="Darwin"),
        patch("platform.machine", return_value="arm64"),
    ):
        url = get_download_url()
        assert (
            url
            == "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-darwin-arm64.tgz"
        )

    # 6. Unsupported system
    with (
        patch("platform.system", return_value="FreeBSD"),
        patch("platform.machine", return_value="amd64"),
    ):
        url = get_download_url()
        assert url is None


def test_get_cloudflared_path_in_path():
    # If cloudflared is already in PATH, it should return that path and NOT download anything
    with patch("shutil.which", return_value="/usr/bin/cloudflared") as mock_which:
        path = get_cloudflared_path()
        assert path == "/usr/bin/cloudflared"
        mock_which.assert_called_with("cloudflared")


def test_get_cloudflared_path_in_gangway_bin():
    # If cloudflared is not in PATH, but exists in ~/.gangway/bin/cloudflared, it should use that path
    with (
        patch("shutil.which", return_value=None),
        patch("pathlib.Path.home", return_value=Path("/home/user")),
        patch.object(Path, "exists", return_value=True) as mock_exists,
    ):
        path = get_cloudflared_path()
        assert "cloudflared" in path
        mock_exists.assert_called()


def test_get_cloudflared_path_download():
    # If not on PATH and not in ~/.gangway/bin, it should download it
    # We must mock urllib.request.urlretrieve and os.chmod and os.makedirs and Path.exists and os.replace
    with (
        patch("shutil.which", return_value=None),
        patch.object(Path, "exists", return_value=False),
        patch("os.makedirs") as mock_makedirs,
        patch("urllib.request.urlretrieve") as mock_urlretrieve,
        patch("os.chmod") as mock_chmod,
        patch("os.replace") as mock_replace,
        patch("platform.system", return_value="Linux"),
        patch("platform.machine", return_value="x86_64"),
        patch("pathlib.Path.home", return_value=Path("/home/user")),
    ):
        path = get_cloudflared_path()
        assert path == str(Path("/home/user/.gangway/bin/cloudflared"))

        # Verify mkdirs is called
        mock_makedirs.assert_called()
        # Verify urlretrieve was called with the correct download URL and target destination path
        mock_urlretrieve.assert_called_once()
        args, kwargs = mock_urlretrieve.call_args
        assert (
            args[0]
            == "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64"
        )
        assert "cloudflared" in args[1]

        # Verify chmod 0o755 was called on Linux
        mock_chmod.assert_called_once()
        assert mock_chmod.call_args[0][1] == 0o755

        # Verify replace was called
        mock_replace.assert_called_once()
        replace_args, _ = mock_replace.call_args
        assert str(replace_args[0]).endswith("cloudflared.tmp")
        assert str(replace_args[1]).endswith("cloudflared")


def test_get_cloudflared_path_download_failure():
    # If download fails, it should delete the temporary file if it exists
    with (
        patch("shutil.which", return_value=None),
        patch("os.makedirs"),
        patch("urllib.request.urlretrieve", side_effect=Exception("Download failed")),
        patch("platform.system", return_value="Linux"),
        patch("platform.machine", return_value="x86_64"),
        patch("pathlib.Path.home", return_value=Path("/home/user")),
        patch("os.remove") as mock_remove,
        patch.object(Path, "exists", autospec=True) as mock_exists,
    ):

        def path_exists_side_effect(*args, **kwargs):
            if args:
                return str(args[0]).endswith(".tmp")
            return False

        mock_exists.side_effect = path_exists_side_effect

        path = get_cloudflared_path()
        assert path is None
        mock_remove.assert_called_once()
        args, _ = mock_remove.call_args
        assert str(args[0]).endswith("cloudflared.tmp")


def test_start_tunnel_background_success():
    # Mock subprocess.Popen
    mock_process = MagicMock()
    mock_process.poll.return_value = None

    # Simulate cloudflared outputting the trycloudflare URL
    # cloudflared logs typically write to stderr:
    # "Your quick tunnel has been created! Visit: https://some-subdomain.trycloudflare.com"
    log_lines = [
        b"2026-06-26T00:00:00Z INF Starting tunnel",
        b"2026-06-26T00:00:01Z INF Your quick tunnel has been created! Visit: https://test-tunnel.trycloudflare.com",
        b"2026-06-26T00:00:02Z INF Connected to tunnel",
    ]
    mock_process.stderr.readline.side_effect = log_lines + [b""]

    with (
        patch("shutil.which", return_value="/usr/bin/cloudflared"),
        patch("subprocess.Popen", return_value=mock_process) as mock_popen,
        patch("gangway.core.tunnel.print_mcp_configs") as mock_print_configs,
    ):
        public_url = start_tunnel_background(port=8000, token="secret")

        assert public_url == "https://test-tunnel.trycloudflare.com"
        mock_popen.assert_called_once()
        mock_print_configs.assert_called_once_with(
            "https://test-tunnel.trycloudflare.com", "secret", host="127.0.0.1"
        )


def test_start_tunnel_background_timeout():
    mock_process = MagicMock()
    mock_process.poll.return_value = None
    mock_process.stderr.readline.side_effect = [b"some random output with no url", b""]

    # We patch time.sleep to avoid waiting during test
    with (
        patch("shutil.which", return_value="/usr/bin/cloudflared"),
        patch("subprocess.Popen", return_value=mock_process),
        patch("time.sleep"),
        pytest.raises(RuntimeError, match="Timeout waiting for Cloudflare tunnel URL"),
    ):
        # Set a short timeout for the test
        start_tunnel_background(port=8000, token="secret", timeout=0.1)


def test_stop_tunnel():
    mock_process = MagicMock()
    mock_process.poll.return_value = None

    with (
        patch("shutil.which", return_value="/usr/bin/cloudflared"),
        patch("subprocess.Popen", return_value=mock_process),
        patch("gangway.core.tunnel.print_mcp_configs"),
    ):
        # First start a tunnel to set the global process variable
        log_lines = [
            b"Your quick tunnel has been created! Visit: https://test.trycloudflare.com"
        ]
        mock_process.stderr.readline.side_effect = log_lines + [b""]
        start_tunnel_background(8000, None)

        # Now stop it
        stop_tunnel()

        # Verify terminate or kill was called
        mock_process.terminate.assert_called_once()
        mock_process.wait.assert_called_once()


def test_start_tunnel_background_host_resolution():
    mock_process = MagicMock()
    mock_process.poll.return_value = None
    log_lines = [
        b"Your quick tunnel has been created! Visit: https://test-tunnel.trycloudflare.com"
    ]
    mock_process.stderr.readline.side_effect = log_lines + [b""]

    with (
        patch("shutil.which", return_value="/usr/bin/cloudflared"),
        patch("subprocess.Popen", return_value=mock_process) as mock_popen,
        patch("gangway.core.tunnel.print_mcp_configs") as mock_print_configs,
    ):
        # 1. Test host "0.0.0.0" maps to "127.0.0.1" for proxy target
        start_tunnel_background(port=8000, token="secret", host="0.0.0.0")
        mock_popen.assert_called_once()
        cmd_args = mock_popen.call_args[0][0]
        assert "http://127.0.0.1:8000" in cmd_args
        mock_print_configs.assert_called_once_with(
            "https://test-tunnel.trycloudflare.com", "secret", host="0.0.0.0"
        )

        mock_popen.reset_mock()
        mock_print_configs.reset_mock()
        mock_process.stderr.readline.side_effect = log_lines + [b""]

        # 2. Test specific host (e.g. "localhost") passes through
        start_tunnel_background(port=8000, token="secret", host="localhost")
        cmd_args = mock_popen.call_args[0][0]
        assert "http://localhost:8000" in cmd_args
        mock_print_configs.assert_called_once_with(
            "https://test-tunnel.trycloudflare.com", "secret", host="localhost"
        )


def test_get_cloudflared_path_download_darwin_tgz():
    # Verify downloading and extracting a tgz file for Darwin arm64 works
    with (
        patch("shutil.which", return_value=None),
        patch("pathlib.Path.home", return_value=Path("/home/user")),
        patch("os.makedirs"),
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
        assert (
            url
            == "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-darwin-arm64.tgz"
        )

        # Verify tarfile open and extraction
        mock_tar_open.assert_called_once()
        open_args = mock_tar_open.call_args[0]
        assert str(open_args[0]).endswith("cloudflared.tgz")
        assert open_args[1] == "r:gz"

        mock_tar.getmember.assert_called_once_with("cloudflared")
        mock_tar.extract.assert_called_once_with(
            mock_member, path=str(Path("/home/user/.gangway/bin"))
        )

        # Verify temp tgz file removal
        mock_remove.assert_called_once()
        assert str(mock_remove.call_args[0][0]).endswith("cloudflared.tgz")

        # Verify executable chmod on the final bin path
        mock_chmod.assert_called_once_with(
            Path("/home/user/.gangway/bin/cloudflared"), 0o755
        )


def test_print_mcp_configs(capsys):
    from gangway.core.tunnel import print_mcp_configs

    # 1. Test printing with token
    print_mcp_configs(
        "https://example.trycloudflare.com", "my_secret_token", "127.0.0.1"
    )
    captured = capsys.readouterr()

    assert "https://example.trycloudflare.com/sse?token=my_secret_token" in captured.out
    assert "mcpServers" in captured.out
    assert "gangway" in captured.out
    assert (
        '"url": "https://example.trycloudflare.com/sse?token=my_secret_token"'
        in captured.out
    )

    # 2. Test printing without token
    print_mcp_configs("https://example.trycloudflare.com", None, "127.0.0.1")
    captured2 = capsys.readouterr()

    assert "https://example.trycloudflare.com/sse" in captured2.out
    assert "token=" not in captured2.out
