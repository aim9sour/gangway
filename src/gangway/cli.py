import argparse
import sys
from gangway.core.config import load_config
from gangway.server.mcp import start_stdio_server, start_sse_server


def main():
    parser = argparse.ArgumentParser(
        description="Gangway - The smart Agent-to-Server Bridge"
    )
    parser.add_argument("--config", help="Path to config file (JSON/TOML)")
    parser.add_argument("--token", help="Bearer token for authentication")
    parser.add_argument(
        "--allowed-root", help="Limit filesystem actions under this directory"
    )
    parser.add_argument("--port", type=int, help="Port to run SSE server on")
    parser.add_argument("--host", help="Host to bind SSE server to")
    parser.add_argument(
        "--transport",
        choices=["stdio", "sse"],
        default="stdio",
        help="Transport mechanism",
    )

    args = parser.parse_args()

    try:
        cfg = load_config(
            config_file=args.config,
            token=args.token,
            allowed_root=args.allowed_root,
            port=args.port,
            host=args.host,
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
