import asyncio
from mcp.server.stdio import stdio_server

from ..config import logger
from ..server import app, state, session_registry, ohlcv_aggregator, ohlcv_store
from ..market.stream import connect_and_stream


async def _main():
    logger.info("Starting WebSocket streaming task...")
    stream_task = asyncio.create_task(
        connect_and_stream(state, session_registry, ohlcv_aggregator, ohlcv_store)
    )

    try:
        logger.info("Starting MCP server over stdio...")
        async with stdio_server() as (read_stream, write_stream):
            await app.run(read_stream, write_stream, app.create_initialization_options())
    finally:
        stream_task.cancel()
        try:
            await stream_task
        except asyncio.CancelledError:
            pass


def main():
    """Entry point wrapper for console_scripts."""
    asyncio.run(_main())


if __name__ == "__main__":
    main()
