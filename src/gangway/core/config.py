import os
import json
from dataclasses import dataclass
from typing import Optional


@dataclass
class Config:
    token: Optional[str] = None
    allowed_root: Optional[str] = None
    port: int = 8000
    host: str = "127.0.0.1"


def load_config(
    config_file: Optional[str] = None,
    token: Optional[str] = None,
    allowed_root: Optional[str] = None,
    port: Optional[int] = None,
    host: Optional[str] = None,
) -> Config:
    # 1. Start with defaults
    cfg = Config()

    # 2. Apply Env Vars
    env_token = os.getenv("GANGWAY_TOKEN")
    env_root = os.getenv("GANGWAY_ALLOWED_ROOT")
    env_port = os.getenv("GANGWAY_PORT")
    env_host = os.getenv("GANGWAY_HOST")

    if env_token:
        cfg.token = env_token
    if env_root:
        cfg.allowed_root = env_root
    if env_port:
        cfg.port = int(env_port)
    if env_host:
        cfg.host = env_host

    # 3. Apply Config File (supports JSON/TOML)
    if config_file and os.path.exists(config_file):
        with open(config_file, "r") as f:
            data = {}
            if config_file.endswith(".json"):
                data = json.load(f)
            elif config_file.endswith(".toml"):
                # fallback minimal parser
                import sys

                if sys.version_info >= (3, 11):
                    import tomllib

                    with open(config_file, "rb") as bf:
                        data = tomllib.load(bf)
                else:
                    try:
                        import tomli as toml

                        with open(config_file, "rb") as bf:
                            data = toml.load(bf)
                    except ImportError:
                        pass

            if "token" in data:
                cfg.token = data["token"]
            if "allowed_root" in data:
                cfg.allowed_root = data["allowed_root"]
            if "port" in data:
                cfg.port = int(data["port"])
            if "host" in data:
                cfg.host = data["host"]

    # 4. Apply CLI values
    if token is not None:
        cfg.token = token
    if allowed_root is not None:
        cfg.allowed_root = allowed_root
    if port is not None:
        cfg.port = port
    if host is not None:
        cfg.host = host

    return cfg
