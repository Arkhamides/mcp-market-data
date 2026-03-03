import asyncio
from mcp.server import Server
from mcp.server.stdio import stdio_server

from .state import MarketState
from .stream import connect_and_stream
from . import tools as tools_module
from .config import logger

app = Server("market-stream-server")
state = MarketState()

@app.list_tools()
async def _list_tools():
    return tools_module.list_tools()

@app.call_tool()
async def _call_tool(name, arguments):
    return await tools_module.call_tool(name, arguments, state)

async def _main():
    logger.info("Starting WebSocket streaming task...")
    stream_task = asyncio.create_task(connect_and_stream(state))

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
