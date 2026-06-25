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
                (b"host", b"localhost")
            ],
            "query_string": b"",
            "path": "/sse",
            "root_path": "",
        }
        sse_request = Request(sse_scope, receive=mock_receive, send=mock_send)

        async with anyio.create_task_group() as tg:
            tg.start_soon(mcp_server.handle_sse, sse_request)
            await anyio.sleep(0.1)
            assert any(msg.get("type") == "http.response.start" and msg.get("status") == 200 for msg in sent_messages)
            tg.cancel_scope.cancel()

        # Test 2: Access SSE with query param
        sent_messages.clear()
        sse_scope["headers"] = [(b"host", b"localhost")]
        sse_scope["query_string"] = b"token=secret_key"
        sse_request = Request(sse_scope, receive=mock_receive, send=mock_send)

        async with anyio.create_task_group() as tg:
            tg.start_soon(mcp_server.handle_sse, sse_request)
            await anyio.sleep(0.1)
            assert any(msg.get("type") == "http.response.start" and msg.get("status") == 200 for msg in sent_messages)
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
                (b"host", b"localhost")
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
                while not any(msg.get("type") == "http.response.body" for msg in sent_messages):
                    await anyio.sleep(0.01)

                body_msg = next(msg for msg in sent_messages if msg.get("type") == "http.response.body")
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
                            (b"authorization", b"Bearer secret_key"),
                            (b"content-type", b"application/json"),
                            (b"host", b"localhost")
                        ],
                        "query_string": f"session_id={session_id}".encode(),
                        "path": "/messages/",
                        "root_path": "",
                    }
                    post_request = Request(post_scope, receive=post_receive, send=post_send)
                    await mcp_server.handle_messages_post(post_request)
                    assert any(msg.get("type") == "http.response.start" and msg.get("status") == 202 for msg in post_sent)

                # 1. Send initialize request
                await send_post({
                    "jsonrpc": "2.0",
                    "method": "initialize",
                    "params": {
                        "protocolVersion": "2024-11-05",
                        "capabilities": {},
                        "clientInfo": {
                            "name": "test-client",
                            "version": "1.0.0"
                        }
                    },
                    "id": 1
                })

                # Wait for initialize response
                while len([msg for msg in sent_messages if msg.get("type") == "http.response.body"]) < 2:
                    await anyio.sleep(0.01)

                # 2. Send initialized notification
                await send_post({
                    "jsonrpc": "2.0",
                    "method": "notifications/initialized"
                })

                # 3. Send tool call request
                await send_post({
                    "jsonrpc": "2.0",
                    "method": "tools/call",
                    "params": {
                        "name": "get_working_directory",
                        "arguments": {}
                    },
                    "id": 2
                })

                # Wait for tool call response (should be 3rd body event)
                while len([msg for msg in sent_messages if msg.get("type") == "http.response.body"]) < 3:
                    await anyio.sleep(0.01)

                body_msgs = [msg for msg in sent_messages if msg.get("type") == "http.response.body"]
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

