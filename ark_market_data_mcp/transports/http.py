"""HTTP/Streamable transport for the MCP market data server.

Uses the Streamable HTTP transport (MCP 1.26+) which provides bidirectional
communication over a single HTTP POST endpoint (/mcp) instead of the older
SSE transport. This is compatible with Claude Code v1.26+ and other modern
MCP clients.

Usage:
    ark-market-data-mcp-http

Environment variables:
    HTTP_HOST  — bind address (default: 0.0.0.0)
    HTTP_PORT  — bind port    (default: 3001)
    WS_URI     — upstream WebSocket endpoint (see config.py)
"""

import asyncio
import contextlib
import os
from collections.abc import AsyncIterator

import uvicorn
from starlette.applications import Starlette
from starlette.middleware.cors import CORSMiddleware
from starlette.requests import Request
from starlette.responses import Response
from starlette.routing import Mount, Route
from mcp.server.streamable_http_manager import StreamableHTTPSessionManager

from ..config import logger
from ..server import app, state
from ..market.stream import connect_and_stream


def _build_starlette_app() -> Starlette:
    session_manager = StreamableHTTPSessionManager(app=app, stateless=False)

    @contextlib.asynccontextmanager
    async def lifespan(starlette_app: Starlette) -> AsyncIterator[None]:
        async with session_manager.run():
            yield

    async def root(request: Request) -> Response:
        return Response("MCP Server running. Connect to /mcp for MCP.")

    async def handle_mcp(scope, receive, send):
        await session_manager.handle_request(scope, receive, send)

    starlette_app = Starlette(
        lifespan=lifespan,
        routes=[
            Route("/", endpoint=root),
            Mount("/mcp", app=handle_mcp),
        ],
    )

    return CORSMiddleware(
        app=starlette_app,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
        allow_credentials=True,
    )


async def _main() -> None:
    host = os.getenv("HTTP_HOST", "0.0.0.0")
    port = int(os.getenv("HTTP_PORT", "3001"))

    logger.info("Starting WebSocket streaming task...")
    stream_task = asyncio.create_task(connect_and_stream(state))

    config = uvicorn.Config(
        app=_build_starlette_app(),
        host=host,
        port=port,
        log_level="info",
    )
    server = uvicorn.Server(config)

    logger.info("Starting MCP server over HTTP/Streamable on %s:%s ...", host, port)
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
