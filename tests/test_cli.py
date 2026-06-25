import sys
import pytest
from unittest.mock import patch
from gangway.cli import main


def test_cli_parsing_stdio():
    test_args = [
        "cli.py",
        "--token",
        "secret",
        "--allowed-root",
        "/tmp",
        "--transport",
        "stdio",
    ]
    with patch.object(sys, "argv", test_args):
        with patch("gangway.cli.start_stdio_server") as mock_stdio:
            main()
            mock_stdio.assert_called_once()
            cfg = mock_stdio.call_args[0][0]
            assert cfg.token == "secret"
            assert (
                str(cfg.allowed_root) == "C:\\tmp"
                if sys.platform == "win32"
                else "/tmp"
            )


def test_cli_parsing_sse():
    test_args = [
        "cli.py",
        "--token",
        "sse-secret",
        "--port",
        "8888",
        "--host",
        "127.0.0.1",
        "--transport",
        "sse",
    ]
    with patch.object(sys, "argv", test_args):
        with patch("gangway.cli.start_sse_server") as mock_sse:
            main()
            mock_sse.assert_called_once()
            cfg = mock_sse.call_args[0][0]
            assert cfg.token == "sse-secret"
            assert cfg.port == 8888
            assert cfg.host == "127.0.0.1"


def test_cli_config_error():
    # If load_config raises an exception, sys.exit(1) should be called
    test_args = ["cli.py"]
    with patch.object(sys, "argv", test_args):
        with patch("gangway.cli.load_config", side_effect=ValueError("Invalid config")):
            with pytest.raises(SystemExit) as excinfo:
                main()
            assert excinfo.value.code == 1


def test_cli_parsing_sse_tunnel():
    test_args = [
        "cli.py",
        "--transport",
        "sse",
        "--tunnel",
    ]
    with patch.object(sys, "argv", test_args):
        with patch("gangway.cli.start_sse_server") as mock_sse:
            main()
            mock_sse.assert_called_once()
            cfg = mock_sse.call_args[0][0]
            assert cfg.tunnel is True

