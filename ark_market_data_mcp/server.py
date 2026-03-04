from mcp.server import Server

from .state import MarketState
from . import tools as tools_module

app = Server("market-stream-server")
state = MarketState()

@app.list_tools()
async def _list_tools():
    return tools_module.list_tools()

@app.call_tool()
async def _call_tool(name, arguments):
    return await tools_module.call_tool(name, arguments, state)
