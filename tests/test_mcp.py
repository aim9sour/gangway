import os
import json
import tempfile
from pathlib import Path
import anyio
from starlette.testclient import TestClient
from gangway.core.config import Config
from gangway.core.state import StateManager
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


def test_mcp_sse_server_auth_success():
    cfg = Config(token="secret_key")
    mcp_server.config = cfg

    client = TestClient(mcp_server.app)

    # 1. Access SSE with header
    response = client.get("/sse", headers={"Authorization": "Bearer secret_key"})
    assert response.status_code == 200

    # 2. Access SSE with query param
    response = client.get("/sse?token=secret_key")
    assert response.status_code == 200


def test_mcp_list_tools():
    async def run():
        tools = await mcp_server.handle_list_tools()
        assert len(tools) > 0
        assert any(t.name == "list_directory" for t in tools)

    anyio.run(run)


def test_mcp_call_tool_list_directory():
    with tempfile.TemporaryDirectory() as tmpdir:
        # Resolve path to match StateManager behavior
        tmpdir_resolved = str(Path(tmpdir).resolve())
        cfg = Config(token="secret_key", allowed_root=tmpdir_resolved)
        mcp_server.config = cfg
        mcp_server.state_manager = StateManager(allowed_root=tmpdir_resolved)

        # Create a dummy file
        with open(os.path.join(tmpdir_resolved, "test.txt"), "w") as f:
            f.write("hello")

        async def run():
            result = await mcp_server.handle_call_tool("list_directory", {"path": "."})
            assert not result.isError
            assert len(result.content) == 1
            content = json.loads(result.content[0].text)
            assert any(entry["name"] == "test.txt" for entry in content)

        anyio.run(run)


def test_mcp_working_directory_tools():
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir_resolved = str(Path(tmpdir).resolve())
        cfg = Config(token="secret_key", allowed_root=tmpdir_resolved)
        mcp_server.config = cfg
        mcp_server.state_manager = StateManager(allowed_root=tmpdir_resolved)

        subdir = os.path.join(tmpdir_resolved, "sub")
        os.makedirs(subdir, exist_ok=True)

        async def run():
            # 1. Get initial working directory
            res = await mcp_server.handle_call_tool("get_working_directory", {})
            assert not res.isError
            assert res.content[0].text == tmpdir_resolved

            # 2. Change working directory
            res = await mcp_server.handle_call_tool(
                "change_working_directory", {"path": "sub"}
            )
            assert not res.isError
            assert "Working directory changed to" in res.content[0].text

            # 3. Verify get working directory returns updated dir
            res = await mcp_server.handle_call_tool("get_working_directory", {})
            assert not res.isError
            assert res.content[0].text == subdir

        anyio.run(run)
