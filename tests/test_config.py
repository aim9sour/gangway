import os
import tempfile
import json
from pathlib import Path
from gangway.core.config import load_config


def test_load_config_precedence():
    # Setup temp config file
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump({"token": "file_token", "port": 9000}, f)
        config_path = f.name

    try:
        # Set Env variables
        os.environ["GANGWAY_TOKEN"] = "env_token"
        os.environ["GANGWAY_PORT"] = "8000"
        os.environ["GANGWAY_ALLOWED_ROOT"] = "/env/root"

        # Scenario 1: Default + Env
        cfg1 = load_config()
        assert cfg1.token == "env_token"
        assert cfg1.port == 8000
        assert cfg1.allowed_root == str(Path("/env/root").resolve())

        # Scenario 2: File overrides env
        cfg2 = load_config(config_file=config_path)
        assert cfg2.token == "file_token"
        assert cfg2.port == 9000
        assert cfg2.allowed_root == str(Path("/env/root").resolve())

        # Scenario 3: CLI overrides file
        cfg3 = load_config(config_file=config_path, token="cli_token", port=9500)
        assert cfg3.token == "cli_token"
        assert cfg3.port == 9500
    finally:
        os.unlink(config_path)
        os.environ.pop("GANGWAY_TOKEN", None)
        os.environ.pop("GANGWAY_PORT", None)
        os.environ.pop("GANGWAY_ALLOWED_ROOT", None)


def test_load_config_defaults():
    # Make sure env vars are cleared
    os.environ.pop("GANGWAY_TOKEN", None)
    os.environ.pop("GANGWAY_PORT", None)
    os.environ.pop("GANGWAY_ALLOWED_ROOT", None)
    os.environ.pop("GANGWAY_HOST", None)

    cfg = load_config()
    assert cfg.token is None
    assert cfg.allowed_root is None
    assert cfg.port == 8000
    assert cfg.host == "127.0.0.1"


def test_load_config_toml():
    with tempfile.NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as f:
        f.write('token = "toml_token"\nport = 9200\n')
        config_path = f.name

    try:
        cfg = load_config(config_file=config_path)
        assert cfg.token == "toml_token"
        assert cfg.port == 9200
    finally:
        os.unlink(config_path)


def test_load_config_missing_file():
    import pytest
    with pytest.raises(FileNotFoundError):
        load_config(config_file="non_existent_file.json")


def test_load_config_allowed_root_resolution():
    # Test relative path resolution
    relative_path = "./some_rel_path"
    cfg = load_config(allowed_root=relative_path)
    from pathlib import Path
    expected = str(Path(relative_path).resolve())
    assert cfg.allowed_root == expected


def test_load_config_invalid_ports():
    import pytest

    # 1. Invalid port in environment variables
    os.environ["GANGWAY_PORT"] = "invalid_port"
    try:
        with pytest.raises(ValueError) as excinfo:
            load_config()
        assert "Invalid port in environment variable GANGWAY_PORT" in str(excinfo.value)
    finally:
        os.environ.pop("GANGWAY_PORT", None)

    # 2. Invalid port in config file
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump({"port": "invalid_port"}, f)
        config_path = f.name
    try:
        with pytest.raises(ValueError) as excinfo:
            load_config(config_file=config_path)
        assert "Invalid port in configuration file" in str(excinfo.value)
    finally:
        os.unlink(config_path)

    # 3. Invalid port in CLI args
    with pytest.raises(ValueError) as excinfo:
        load_config(port="invalid_port")
    assert "Invalid port" in str(excinfo.value)


