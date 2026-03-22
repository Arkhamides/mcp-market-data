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

import websockets
import uvicorn
from starlette.applications import Starlette
from starlette.middleware.cors import CORSMiddleware
from starlette.requests import Request
from starlette.responses import Response
from starlette.routing import Mount, Route, WebSocketRoute
from starlette.websockets import WebSocket, WebSocketDisconnect
from mcp.server.streamable_http_manager import StreamableHTTPSessionManager

from ..config import WS_URI, logger
from ..server import app, state, session_registry, ohlcv_aggregator, ohlcv_store
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

    async def ws_proxy(websocket: WebSocket):
        await websocket.accept()
        try:
            async with websockets.connect(WS_URI) as upstream:
                async def upstream_to_client():
                    async for message in upstream:
                        await websocket.send_text(message)

                async def client_to_upstream():
                    while True:
                        data = await websocket.receive_text()
                        await upstream.send(data)

                tasks = [
                    asyncio.create_task(upstream_to_client()),
                    asyncio.create_task(client_to_upstream()),
                ]
                try:
                    await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
                finally:
                    for t in tasks:
                        t.cancel()
                    await asyncio.gather(*tasks, return_exceptions=True)
        except (WebSocketDisconnect, Exception):
            pass
        finally:
            with contextlib.suppress(Exception):
                await websocket.close()

    starlette_app = Starlette(
        lifespan=lifespan,
        routes=[
            Route("/", endpoint=root),
            Mount("/mcp", app=handle_mcp),
            WebSocketRoute("/websocket", endpoint=ws_proxy),
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
    stream_task = asyncio.create_task(
        connect_and_stream(state, session_registry, ohlcv_aggregator, ohlcv_store)
    )

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
