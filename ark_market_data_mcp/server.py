from mcp.server import Server

from .state import MarketState, SessionRegistry
from .market.ohlcv import OHLCVAggregator
from .market.store import OHLCVStore
from . import tools as tools_module

app = Server("market-stream-server")
state = MarketState()
session_registry = SessionRegistry()
ohlcv_aggregator = OHLCVAggregator()
ohlcv_store = OHLCVStore()

@app.list_tools()
async def _list_tools():
    return tools_module.list_tools()

@app.call_tool()
async def _call_tool(name, arguments):
    return await tools_module.call_tool(
        name, arguments, app, state, session_registry, ohlcv_store
    )
