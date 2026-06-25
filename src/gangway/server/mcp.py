import json
import logging
from typing import Optional
from mcp.server.lowlevel.server import Server
import mcp.types as types
import mcp.server.stdio
from mcp.server.sse import SseServerTransport

from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import Response
from starlette.exceptions import HTTPException
from starlette.routing import Route

from gangway.core.config import Config, load_config
from gangway.core.state import StateManager
from gangway.core.jobs import JobManager
import gangway.core.files as files_core

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("gangway.mcp")

server = Server("gangway", "0.1.0")

state_manager: Optional[StateManager] = None
job_manager: Optional[JobManager] = None
config: Optional[Config] = None


def ensure_globals():
    global config, state_manager, job_manager
    if config is None:
        config = load_config()
    if state_manager is None:
        state_manager = StateManager(allowed_root=config.allowed_root)
    if job_manager is None:
        job_manager = JobManager(allowed_root=config.allowed_root)


@server.list_tools()
async def handle_list_tools():
    ensure_globals()
    return [
        types.Tool(
            name="list_directory",
            description="List contents of a directory.",
            inputSchema={
                "type": "object",
                "properties": {"path": {"type": "string", "default": "."}},
            },
        ),
        types.Tool(
            name="glob_search",
            description="Search for files recursively using glob.",
            inputSchema={
                "type": "object",
                "properties": {"pattern": {"type": "string"}},
                "required": ["pattern"],
            },
        ),
        types.Tool(
            name="preview_file",
            description="Preview a file.",
            inputSchema={
                "type": "object",
                "properties": {
                    "path": {"type": "string"},
                    "head": {"type": "integer", "default": 80},
                    "tail": {"type": "integer", "default": 40},
                },
                "required": ["path"],
            },
        ),
        types.Tool(
            name="project_overview",
            description="Overview of the repository.",
            inputSchema={
                "type": "object",
                "properties": {"path": {"type": "string", "default": "."}},
            },
        ),
        types.Tool(
            name="upload_chunk",
            description="Upload a base64 chunk.",
            inputSchema={
                "type": "object",
                "properties": {
                    "file_path": {"type": "string"},
                    "chunk_index": {"type": "integer"},
                    "total_chunks": {"type": "integer"},
                    "data_b64": {"type": "string"},
                },
                "required": ["file_path", "chunk_index", "total_chunks", "data_b64"],
            },
        ),
        types.Tool(
            name="assemble_upload",
            description="Assemble chunks.",
            inputSchema={
                "type": "object",
                "properties": {
                    "file_path": {"type": "string"},
                    "total_chunks": {"type": "integer"},
                },
                "required": ["file_path", "total_chunks"],
            },
        ),
        types.Tool(
            name="download_chunk",
            description="Download chunk.",
            inputSchema={
                "type": "object",
                "properties": {
                    "file_path": {"type": "string"},
                    "chunk_index": {"type": "integer"},
                    "chunk_size": {"type": "integer", "default": 65536},
                },
                "required": ["file_path", "chunk_index"],
            },
        ),
        types.Tool(
            name="compress_archive",
            description="Compress directory.",
            inputSchema={
                "type": "object",
                "properties": {
                    "archive_path": {"type": "string"},
                    "source_dir": {"type": "string"},
                    "format": {
                        "type": "string",
                        "enum": ["zip", "tar.gz"],
                        "default": "zip",
                    },
                },
                "required": ["archive_path", "source_dir"],
            },
        ),
        types.Tool(
            name="extract_archive",
            description="Extract archive.",
            inputSchema={
                "type": "object",
                "properties": {
                    "archive_path": {"type": "string"},
                    "extract_dir": {"type": "string"},
                },
                "required": ["archive_path", "extract_dir"],
            },
        ),
        types.Tool(
            name="get_working_directory",
            description="Get active working directory.",
            inputSchema={"type": "object", "properties": {}},
        ),
        types.Tool(
            name="change_working_directory",
            description="Change active working directory.",
            inputSchema={
                "type": "object",
                "properties": {"path": {"type": "string"}},
                "required": ["path"],
            },
        ),
        types.Tool(
            name="start_background_job",
            description="Start a background job.",
            inputSchema={
                "type": "object",
                "properties": {"cmd": {"type": "string"}, "cwd": {"type": "string"}},
                "required": ["cmd"],
            },
        ),
        types.Tool(
            name="get_job_status",
            description="Get job status.",
            inputSchema={
                "type": "object",
                "properties": {"job_id": {"type": "string"}},
                "required": ["job_id"],
            },
        ),
        types.Tool(
            name="list_background_jobs",
            description="List background jobs.",
            inputSchema={"type": "object", "properties": {}},
        ),
        types.Tool(
            name="read_job_logs",
            description="Read job logs.",
            inputSchema={
                "type": "object",
                "properties": {
                    "job_id": {"type": "string"},
                    "head": {"type": "integer", "default": 100},
                    "tail": {"type": "integer", "default": 100},
                },
                "required": ["job_id"],
            },
        ),
        types.Tool(
            name="kill_background_job",
            description="Kill a job.",
            inputSchema={
                "type": "object",
                "properties": {"job_id": {"type": "string"}},
                "required": ["job_id"],
            },
        ),
    ]


@server.call_tool()
async def handle_call_tool(name: str, arguments: dict):
    ensure_globals()
    try:
        if name == "list_directory":
            raw_path = arguments.get("path", ".")
            resolved = state_manager.resolve_path(raw_path)
            res = files_core.list_directory(resolved, config.allowed_root)
            return types.CallToolResult(
                content=[types.TextContent(type="text", text=json.dumps(res, indent=2))]
            )

        elif name == "glob_search":
            pattern = arguments["pattern"]
            res = files_core.glob_search(pattern, config.allowed_root)
            return types.CallToolResult(
                content=[types.TextContent(type="text", text=json.dumps(res, indent=2))]
            )

        elif name == "preview_file":
            raw_path = arguments["path"]
            resolved = state_manager.resolve_path(raw_path)
            head = (
                int(arguments.get("head")) if arguments.get("head") is not None else 80
            )
            tail = (
                int(arguments.get("tail")) if arguments.get("tail") is not None else 40
            )
            res = files_core.preview_file(
                resolved, config.allowed_root, head=head, tail=tail
            )
            return types.CallToolResult(
                content=[types.TextContent(type="text", text=res)]
            )

        elif name == "project_overview":
            raw_path = arguments.get("path", ".")
            resolved = state_manager.resolve_path(raw_path)
            res = files_core.project_overview(resolved, config.allowed_root)
            return types.CallToolResult(
                content=[types.TextContent(type="text", text=json.dumps(res, indent=2))]
            )

        elif name == "upload_chunk":
            raw_path = arguments["file_path"]
            resolved = state_manager.resolve_path(raw_path)
            chunk_idx = int(arguments["chunk_index"])
            total_chunks = int(arguments["total_chunks"])
            data_b64 = arguments["data_b64"]
            res = files_core.upload_chunk(
                resolved, chunk_idx, total_chunks, data_b64, config.allowed_root
            )
            return types.CallToolResult(
                content=[types.TextContent(type="text", text=str(res))]
            )

        elif name == "assemble_upload":
            raw_path = arguments["file_path"]
            resolved = state_manager.resolve_path(raw_path)
            total_chunks = int(arguments["total_chunks"])
            res = files_core.assemble_upload(
                resolved, total_chunks, config.allowed_root
            )
            return types.CallToolResult(
                content=[types.TextContent(type="text", text=f"Assembled at: {res}")]
            )

        elif name == "download_chunk":
            raw_path = arguments["file_path"]
            resolved = state_manager.resolve_path(raw_path)
            chunk_idx = int(arguments["chunk_index"])
            chunk_size = (
                int(arguments.get("chunk_size"))
                if arguments.get("chunk_size") is not None
                else 65536
            )
            res = files_core.download_chunk(
                resolved, chunk_idx, chunk_size, config.allowed_root
            )
            return types.CallToolResult(
                content=[types.TextContent(type="text", text=json.dumps(res))]
            )

        elif name == "compress_archive":
            archive_path = arguments["archive_path"]
            resolved_archive = state_manager.resolve_path(archive_path)
            source_dir = arguments["source_dir"]
            resolved_source = state_manager.resolve_path(source_dir)
            fmt = arguments.get("format", "zip")
            res = files_core.compress_archive(
                resolved_archive, resolved_source, config.allowed_root, format=fmt
            )
            return types.CallToolResult(
                content=[
                    types.TextContent(type="text", text=f"Archive created at: {res}")
                ]
            )

        elif name == "extract_archive":
            archive_path = arguments["archive_path"]
            resolved_archive = state_manager.resolve_path(archive_path)
            extract_dir = arguments["extract_dir"]
            resolved_extract = state_manager.resolve_path(extract_dir)
            res = files_core.extract_archive(
                resolved_archive, resolved_extract, config.allowed_root
            )
            return types.CallToolResult(
                content=[types.TextContent(type="text", text=f"Extracted to: {res}")]
            )

        elif name == "get_working_directory":
            return types.CallToolResult(
                content=[types.TextContent(type="text", text=state_manager.get_cwd())]
            )

        elif name == "change_working_directory":
            path = arguments["path"]
            new_cwd = state_manager.set_cwd(path)
            return types.CallToolResult(
                content=[
                    types.TextContent(
                        type="text", text=f"Working directory changed to: {new_cwd}"
                    )
                ]
            )

        elif name == "start_background_job":
            cmd = arguments["cmd"]
            raw_cwd = arguments.get("cwd") or state_manager.get_cwd()
            resolved_cwd = state_manager.resolve_path(raw_cwd)
            job_id = job_manager.start_job(cmd, resolved_cwd)
            return types.CallToolResult(
                content=[types.TextContent(type="text", text=job_id)]
            )

        elif name == "get_job_status":
            job_id = arguments["job_id"]
            status = job_manager.get_job_status(job_id)
            return types.CallToolResult(
                content=[
                    types.TextContent(type="text", text=json.dumps(status, indent=2))
                ]
            )

        elif name == "list_background_jobs":
            jobs_list = job_manager.list_jobs()
            return types.CallToolResult(
                content=[
                    types.TextContent(type="text", text=json.dumps(jobs_list, indent=2))
                ]
            )

        elif name == "read_job_logs":
            job_id = arguments["job_id"]
            head = (
                int(arguments.get("head")) if arguments.get("head") is not None else 100
            )
            tail = (
                int(arguments.get("tail")) if arguments.get("tail") is not None else 100
            )
            logs = job_manager.read_job_logs(job_id, head=head, tail=tail)
            return types.CallToolResult(
                content=[types.TextContent(type="text", text=logs)]
            )

        elif name == "kill_background_job":
            job_id = arguments["job_id"]
            success = job_manager.kill_job(job_id)
            return types.CallToolResult(
                content=[
                    types.TextContent(
                        type="text",
                        text="Job terminated successfully"
                        if success
                        else "Job is not running",
                    )
                ]
            )

        else:
            raise ValueError(f"Unknown tool: {name}")

    except Exception as e:
        logger.error(f"Error calling tool {name}: {e}", exc_info=True)
        return types.CallToolResult(
            content=[
                types.TextContent(type="text", text=f"Error executing {name}: {str(e)}")
            ],
            isError=True,
        )


sse = SseServerTransport("/messages/")


def verify_token(request: Request):
    ensure_globals()
    if not config or not config.token:
        return
    token = request.headers.get("Authorization")
    if token and token.lower().startswith("bearer "):
        token = token[7:]
    else:
        token = request.query_params.get("token")
    if token != config.token:
        raise HTTPException(status_code=401, detail="Unauthorized")


async def handle_sse(request: Request):
    ensure_globals()
    verify_token(request)
    async with sse.connect_sse(request.scope, request.receive, request._send) as (
        read_stream,
        write_stream,
    ):
        await server.run(
            read_stream, write_stream, server.create_initialization_options()
        )
    return Response()


async def handle_messages_post(request: Request):
    ensure_globals()
    verify_token(request)
    return await sse.handle_post_message(request.scope, request.receive, request._send)


app = Starlette(
    routes=[
        Route("/sse", endpoint=handle_sse, methods=["GET"]),
        Route("/messages/", endpoint=handle_messages_post, methods=["POST"]),
    ]
)


def start_sse_server(cfg: Config):
    global config, state_manager, job_manager
    config = cfg
    state_manager = StateManager(allowed_root=cfg.allowed_root)
    job_manager = JobManager(allowed_root=cfg.allowed_root)
    import uvicorn

    if cfg.tunnel:
        from gangway.core.tunnel import start_tunnel_background
        start_tunnel_background(cfg.port, cfg.token)

    logger.info(f"Starting MCP SSE server on {cfg.host}:{cfg.port}")
    uvicorn.run(app, host=cfg.host, port=cfg.port)


def start_stdio_server(cfg: Config):
    global config, state_manager, job_manager
    config = cfg
    state_manager = StateManager(allowed_root=cfg.allowed_root)
    job_manager = JobManager(allowed_root=cfg.allowed_root)
    import anyio

    async def run_stdio():
        async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
            await server.run(
                read_stream, write_stream, server.create_initialization_options()
            )

    logger.info("Starting MCP stdio server")
    anyio.run(run_stdio)
