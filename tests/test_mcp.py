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
    from starlette.requests import Request

    cfg = Config(token="secret_key")
    mcp_server.config = cfg

    async def run():
        # GET Request Setup
        sent_messages = []

        async def mock_send(message: dict):
            sent_messages.append(message)

        disconnect_event = anyio.Event()

        async def mock_receive():
            await disconnect_event.wait()
            return {"type": "http.disconnect"}

        # Test 1: Access SSE with header
        sse_scope = {
            "type": "http",
            "method": "GET",
            "headers": [
                (b"authorization", b"Bearer secret_key"),
                (b"host", b"localhost"),
            ],
            "query_string": b"",
            "path": "/sse",
            "root_path": "",
        }
        sse_request = Request(sse_scope, receive=mock_receive, send=mock_send)

        async with anyio.create_task_group() as tg:
            tg.start_soon(mcp_server.handle_sse, sse_request)
            await anyio.sleep(0.1)
            assert any(
                msg.get("type") == "http.response.start" and msg.get("status") == 200
                for msg in sent_messages
            )
            tg.cancel_scope.cancel()

        # Test 2: Access SSE with query param
        sent_messages.clear()
        sse_scope["headers"] = [(b"host", b"localhost")]
        sse_scope["query_string"] = b"token=secret_key"
        sse_request = Request(sse_scope, receive=mock_receive, send=mock_send)

        async with anyio.create_task_group() as tg:
            tg.start_soon(mcp_server.handle_sse, sse_request)
            await anyio.sleep(0.1)
            assert any(
                msg.get("type") == "http.response.start" and msg.get("status") == 200
                for msg in sent_messages
            )
            tg.cancel_scope.cancel()

    anyio.run(run)


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


def test_mcp_full_client_integration():
    from starlette.requests import Request

    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir_resolved = str(Path(tmpdir).resolve())
        cfg = Config(token="secret_key", allowed_root=tmpdir_resolved)
        mcp_server.config = cfg
        mcp_server.state_manager = StateManager(allowed_root=tmpdir_resolved)
        mcp_server.job_manager = mcp_server.JobManager(allowed_root=tmpdir_resolved)

        # GET Request Setup
        sent_messages = []

        async def mock_send(message: dict):
            sent_messages.append(message)

        disconnect_event = anyio.Event()

        async def mock_receive():
            await disconnect_event.wait()
            return {"type": "http.disconnect"}

        sse_scope = {
            "type": "http",
            "method": "GET",
            "headers": [
                (b"authorization", b"Bearer secret_key"),
                (b"host", b"localhost"),
            ],
            "query_string": b"",
            "path": "/sse",
            "root_path": "",
        }
        sse_request = Request(sse_scope, receive=mock_receive, send=mock_send)

        async def run():
            async with anyio.create_task_group() as tg:
                tg.start_soon(mcp_server.handle_sse, sse_request)

                # Wait for endpoint event
                while not any(
                    msg.get("type") == "http.response.body" for msg in sent_messages
                ):
                    await anyio.sleep(0.01)

                body_msg = next(
                    msg
                    for msg in sent_messages
                    if msg.get("type") == "http.response.body"
                )
                body_str = body_msg["body"].decode()

                session_id = None
                for line in body_str.split("\n"):
                    if "session_id=" in line:
                        session_id = line.split("session_id=")[1].strip()
                        break

                assert session_id is not None

                # Helper function to send POST requests
                async def send_post(payload_dict):
                    payload = json.dumps(payload_dict).encode()
                    post_receive_queue = [
                        {"type": "http.request", "body": payload, "more_body": False}
                    ]

                    async def post_receive():
                        if post_receive_queue:
                            return post_receive_queue.pop(0)
                        return {"type": "http.disconnect"}

                    post_sent = []

                    async def post_send(message: dict):
                        post_sent.append(message)

                    post_scope = {
                        "type": "http",
                        "method": "POST",
                        "headers": [
                            # Note: Real clients do not send authorization headers for POST messages,
                            # they rely on session_id validation.
                            (b"content-type", b"application/json"),
                            (b"host", b"localhost"),
                        ],
                        "query_string": f"session_id={session_id}".encode(),
                        "path": "/messages/",
                        "root_path": "",
                    }
                    post_request = Request(
                        post_scope, receive=post_receive, send=post_send
                    )
                    await mcp_server.handle_messages_post(post_request)
                    assert any(
                        msg.get("type") == "http.response.start"
                        and msg.get("status") == 202
                        for msg in post_sent
                    )

                # 1. Send initialize request
                await send_post(
                    {
                        "jsonrpc": "2.0",
                        "method": "initialize",
                        "params": {
                            "protocolVersion": "2024-11-05",
                            "capabilities": {},
                            "clientInfo": {"name": "test-client", "version": "1.0.0"},
                        },
                        "id": 1,
                    }
                )

                # Wait for initialize response
                while (
                    len(
                        [
                            msg
                            for msg in sent_messages
                            if msg.get("type") == "http.response.body"
                        ]
                    )
                    < 2
                ):
                    await anyio.sleep(0.01)

                # 2. Send initialized notification
                await send_post(
                    {"jsonrpc": "2.0", "method": "notifications/initialized"}
                )

                # 3. Send tool call request
                await send_post(
                    {
                        "jsonrpc": "2.0",
                        "method": "tools/call",
                        "params": {"name": "get_working_directory", "arguments": {}},
                        "id": 2,
                    }
                )

                # Wait for tool call response (should be 3rd body event)
                while (
                    len(
                        [
                            msg
                            for msg in sent_messages
                            if msg.get("type") == "http.response.body"
                        ]
                    )
                    < 3
                ):
                    await anyio.sleep(0.01)

                body_msgs = [
                    msg
                    for msg in sent_messages
                    if msg.get("type") == "http.response.body"
                ]
                tool_response_body = body_msgs[2]["body"].decode()

                data_json = None
                for line in tool_response_body.split("\n"):
                    if line.startswith("data:"):
                        data_json = json.loads(line[5:].strip())
                        break

                assert data_json is not None
                assert data_json["id"] == 2
                assert "result" in data_json
                assert data_json["result"]["content"][0]["text"] == tmpdir_resolved

                # Clean shutdown
                tg.cancel_scope.cancel()

        anyio.run(run)


def test_mcp_bearer_auth_case_insensitive():
    from starlette.requests import Request

    cfg = Config(token="secret_key")
    mcp_server.config = cfg

    # Test lowercase bearer
    async def run_bearer():
        sent_messages = []

        async def mock_send(message: dict):
            sent_messages.append(message)

        disconnect_event = anyio.Event()

        async def mock_receive():
            await disconnect_event.wait()
            return {"type": "http.disconnect"}

        sse_scope = {
            "type": "http",
            "method": "GET",
            "headers": [
                (b"authorization", b"bearer secret_key"),
                (b"host", b"localhost"),
            ],
            "query_string": b"",
            "path": "/sse",
            "root_path": "",
        }
        sse_request = Request(sse_scope, receive=mock_receive, send=mock_send)

        async with anyio.create_task_group() as tg:
            tg.start_soon(mcp_server.handle_sse, sse_request)
            await anyio.sleep(0.1)
            assert any(
                msg.get("type") == "http.response.start" and msg.get("status") == 200
                for msg in sent_messages
            )
            tg.cancel_scope.cancel()

    anyio.run(run_bearer)


def test_mcp_argument_casting():
    import base64

    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir_resolved = str(Path(tmpdir).resolve())
        cfg = Config(token="secret_key", allowed_root=tmpdir_resolved)
        mcp_server.config = cfg
        mcp_server.state_manager = StateManager(allowed_root=tmpdir_resolved)
        mcp_server.job_manager = mcp_server.JobManager(allowed_root=tmpdir_resolved)

        # Create dummy file for preview_file
        with open(os.path.join(tmpdir_resolved, "test_cast.txt"), "w") as f:
            f.write("line1\nline2\nline3")

        async def run_casting():
            # preview_file with head/tail as stringy numeric values
            res = await mcp_server.handle_call_tool(
                "preview_file", {"path": "test_cast.txt", "head": "2", "tail": "1"}
            )
            assert not res.isError
            assert "line1" in res.content[0].text
            assert "line3" in res.content[0].text

            # download_chunk with chunk_index and chunk_size as strings
            with open(os.path.join(tmpdir_resolved, "chunk_test.bin"), "wb") as f:
                f.write(b"hello world")

            res_dl = await mcp_server.handle_call_tool(
                "download_chunk",
                {"file_path": "chunk_test.bin", "chunk_index": "0", "chunk_size": "5"},
            )
            assert not res_dl.isError
            data = json.loads(res_dl.content[0].text)
            assert base64.b64decode(data["data_b64"]) == b"hello"

        anyio.run(run_casting)


def test_start_sse_server_with_tunnel():
    from unittest.mock import patch
    from gangway.core.config import Config

    cfg = Config(tunnel=True, port=8888, token="test_token_tunnel")

    with (
        patch("uvicorn.run") as mock_uvicorn_run,
        patch("gangway.core.tunnel.start_tunnel_background") as mock_start_tunnel,
    ):
        mcp_server.start_sse_server(cfg)

        # Verify uvicorn.run was called
        mock_uvicorn_run.assert_called_once_with(
            mcp_server.app, host=cfg.host, port=cfg.port
        )
        # Verify start_tunnel_background was called
        mock_start_tunnel.assert_called_once_with(cfg.port, cfg.token, host=cfg.host)


def test_start_sse_server_without_tunnel():
    from unittest.mock import patch
    from gangway.core.config import Config

    cfg = Config(tunnel=False, port=8888, token="test_token_no_tunnel")

    with (
        patch("uvicorn.run") as mock_uvicorn_run,
        patch("gangway.core.tunnel.start_tunnel_background") as mock_start_tunnel,
    ):
        mcp_server.start_sse_server(cfg)

        # Verify uvicorn.run was called
        mock_uvicorn_run.assert_called_once_with(
            mcp_server.app, host=cfg.host, port=cfg.port
        )
        # Verify start_tunnel_background was NOT called
        mock_start_tunnel.assert_not_called()


def test_mcp_all_exposed_tools_robustness():
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir_resolved = str(Path(tmpdir).resolve())
        cfg = Config(token="secret_key", allowed_root=tmpdir_resolved)
        mcp_server.config = cfg
        mcp_server.state_manager = StateManager(allowed_root=tmpdir_resolved)
        mcp_server.job_manager = mcp_server.JobManager(allowed_root=tmpdir_resolved)

        async def run_robustness():
            # Handle list tools to get all exposed tools
            tools = await mcp_server.handle_list_tools()
            assert len(tools) == 16  # Exposes exactly 16 tools

            for tool in tools:
                # 1. Validate tool schema structure (must be readable by standard MCP clients)
                assert tool.name, "Tool is missing a name"
                assert tool.description, f"Tool {tool.name} is missing a description"
                assert isinstance(tool.inputSchema, dict), (
                    f"Tool {tool.name} has invalid inputSchema type"
                )
                assert tool.inputSchema.get("type") == "object", (
                    f"Tool {tool.name} schema type is not object"
                )

                # 2. Call tool with empty arguments, verify it returns CallToolResult gracefully
                result = await mcp_server.handle_call_tool(tool.name, {})
                assert isinstance(result, mcp_server.types.CallToolResult), (
                    f"Tool {tool.name} call did not return CallToolResult"
                )

                # Verify that if it is an error, it is marked as isError=True, and contains a text message
                if result.isError:
                    assert len(result.content) > 0, (
                        f"Error response for {tool.name} is empty"
                    )
                    assert result.content[0].type == "text", (
                        "Error response content type is not text"
                    )
                    assert (
                        "Error executing" in result.content[0].text
                        or "missing" in result.content[0].text
                        or "required" in result.content[0].text
                        or "KeyError" in result.content[0].text
                        or "ValueError" in result.content[0].text
                    ), (
                        f"Unexpected error format for {tool.name}: {result.content[0].text}"
                    )

        anyio.run(run_robustness)


def test_mcp_stdio_client_handshake():
    from mcp import ClientSession

    async def run():
        # Create memory streams for bidirectional communication
        # client_write -> server_read
        client_write, server_read = anyio.create_memory_object_stream(10)
        # server_write -> client_read
        server_write, client_read = anyio.create_memory_object_stream(10)

        # Run client session and server in parallel
        async with anyio.create_task_group() as tg:
            # Start server
            tg.start_soon(
                mcp_server.server.run,
                server_read,
                server_write,
                mcp_server.server.create_initialization_options(),
            )

            # Start client session
            async with ClientSession(client_read, client_write) as session:
                # Run initialize handshake
                init_result = await session.initialize()
                assert init_result is not None
                assert init_result.protocolVersion is not None

                # Verify we can list tools via the actual client session
                tools_result = await session.list_tools()
                assert len(tools_result.tools) == 16
                assert any(t.name == "list_directory" for t in tools_result.tools)

            tg.cancel_scope.cancel()

    anyio.run(run)


def test_mcp_sse_cors_preflight():
    cfg = Config(token="secret_key")
    mcp_server.config = cfg
    client = TestClient(mcp_server.app)

    headers = {
        "Origin": "http://localhost:3000",
        "Access-Control-Request-Method": "POST",
        "Access-Control-Request-Headers": "Content-Type",
    }
    response = client.options("/messages/", headers=headers)
    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") == "*"
    assert "POST" in response.headers.get("access-control-allow-methods", "")

    response2 = client.options("/messages", headers=headers)
    assert response2.status_code == 200
    assert response2.headers.get("access-control-allow-origin") == "*"


def test_mcp_sse_no_slash_post_unauthorized():
    cfg = Config(token="secret_key")
    mcp_server.config = cfg
    client = TestClient(mcp_server.app)

    response = client.post("/messages")
    assert response.status_code == 401


def test_mcp_sse_no_slash_post_authorized_empty():
    cfg = Config(token="secret_key")
    mcp_server.config = cfg
    client = TestClient(mcp_server.app)

    response = client.post("/messages?token=secret_key")
    assert response.status_code in (400, 404)


def test_mcp_sse_get_messages_method_not_allowed():
    cfg = Config(token="secret_key")
    mcp_server.config = cfg
    client = TestClient(mcp_server.app)

    response = client.get("/messages?token=secret_key")
    assert response.status_code == 405
