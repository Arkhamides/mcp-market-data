import logging
import os

# WebSocket server URI - read from environment variable, fallback to default
WS_URI = os.getenv("WS_URI", "ws://localhost:9002")

# Message sent to your C++ server to subscribe
SUBSCRIBE_MSG = {"event": "subscribe_aggregated_market"}

# Max messages kept in buffer
MAX_BUFFER_SIZE = 500

# Max concurrent alerts
MAX_ALERTS = 50

# OHLCV local storage directory (override with DATA_DIR env var)
DATA_DIR = os.environ.get("DATA_DIR", os.path.expanduser("~/.ark-market-data"))

# Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("market-mcp")
