"""HTTP/SSE transport for the MCP market data server.

Runs the same MCP app as server.py but over HTTP using Server-Sent Events
instead of stdio. Useful for Docker deployments and remote clients.

Usage:
    ark-market-data-mcp-http

Environment variables:
    HTTP_HOST  — bind address (default: 0.0.0.0)
    HTTP_PORT  — bind port    (default: 8000)
    WS_URI     — upstream WebSocket endpoint (see config.py)
"""

import asyncio
import os

import uvicorn
from mcp.server.sse import SseServerTransport
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import Response
from starlette.routing import Mount, Route

from ..config import logger
from ..server import app, state
from ..market.stream import connect_and_stream

from starlette.middleware.cors import CORSMiddleware

def _build_starlette_app() -> Starlette:
    sse = SseServerTransport("/messages")

    async def handle_sse(request: Request) -> Response:
        async with sse.connect_sse(
            request.scope, request.receive, request._send
        ) as (read_stream, write_stream):
            await app.run(
                read_stream,
                write_stream,
                app.create_initialization_options(),
            )
        return Response()

    starlette_app = Starlette(
        routes=[
            Route("/sse", endpoint=handle_sse),
            Mount("/messages", app=sse.handle_post_message),
        ]
    )

    # 🔥 Add CORS middleware
    starlette_app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # or ["http://localhost:5173"]
        allow_methods=["*"],
        allow_headers=["*"],
        allow_credentials=True,
    )

    return starlette_app



async def _main() -> None:
    host = os.getenv("HTTP_HOST", "0.0.0.0")
    port = int(os.getenv("HTTP_PORT", "8000"))

    logger.info("Starting WebSocket streaming task...")
    stream_task = asyncio.create_task(connect_and_stream(state))

    config = uvicorn.Config(
        app=_build_starlette_app(),
        host=host,
        port=port,
        log_level="info",
    )
    server = uvicorn.Server(config)

    logger.info("Starting MCP server over HTTP/SSE on %s:%s ...", host, port)
    try:
        await server.serve()
    finally:
        stream_task.cancel()
        try:
            await stream_task
        except asyncio.CancelledError:
            pass


def main() -> None:
    """Entry point wrapper for console_scripts."""
    asyncio.run(_main())


if __name__ == "__main__":
    main()
