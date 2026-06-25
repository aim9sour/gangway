# gangway

A smart Agent-to-Server Bridge connecting AI agents (like Cursor and Claude Desktop) to remote environments (Kaggle, Colab, VPS) for full control, functioning as both an MCP server and REST API.

## Features

* **Zero-Dependency Server**: Built using only Python standard library to prevent environment pollution or package conflicts on remote nodes.
* **Context Optimization Tools**: Optimized tools for AIs (e.g., `preview_file`, `project_overview`, fast search) to save context window tokens.
* **Background Job Control**: Execute and monitor long-running tasks asynchronously.
* **Zero-Config Tunneling**: Integrated Cloudflare Tunnel to bypass NAT / firewalls.
* **Directory State Management**: Keep track of the active working directory across execution contexts.

## Installation

```bash
pip install gangway
```
