# Ark Market Data MCP

An MCP (Model Context Protocol) server that streams real-time market data to Claude via WebSocket connection.

## Features

- **Real-time Market Data Streaming** - Connects to a WebSocket server and buffers incoming market data
- **MCP Integration** - Works seamlessly with Claude via the Model Context Protocol
- **Configurable WebSocket URL** - Supports environment variable configuration for flexible deployment
- **In-memory Buffering** - Efficiently buffers up to 500 messages with configurable size
- **Auto-reconnect** - Automatically reconnects on connection failures with exponential backoff

## Installation

### Via PyPI

```bash
pip install ark-market-data-mcp
```

### From Source

```bash
git clone https://github.com/arkhamides/mcp-market-data.git
cd ark-market-data-mcp
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -e .
```

## Quick Start

### 1. Set up your WebSocket endpoint

```bash
export WS_URI=ws://your-websocket-url.com
```

### 2. Add to Claude

```bash
claude mcp add ark-market-data ark-market-data-mcp
```

### 3. Use with Claude

```bash
claude chat
```

Ask Claude to use the market data tools, e.g., "What's the latest market data?"


## Available Tools

The MCP server exposes the following tools for Claude:

- **`get_latest_message`** - Get the most recent market message from the stream
- **`get_recent_messages`** - Get the last N messages (default: 10, max: 500)
- **`get_stream_status`** - Check WebSocket connection status and buffer statistics
- **`clear_buffer`** - Clear the message buffer

## Connecting for the users of the app

### Remote server connection
```
https://mcp-market-data.com/mcp?api=YOUR_API_KEY
```

### Local server connection

```bash
source venv/bin/activate
python3 -m ark_market_data_mcp
```

## Docker (HTTP Transport)

The HTTP transport runs the MCP server over HTTP/SSE, suitable for remote clients and containerised deployments.

### Build the image

```bash
docker build -t ark-market-data-mcp .
```

### Run the container

```bash
docker run -d \
  -p 8000:8000 \
  -e WS_URI=ws://your-websocket-url.com \
  --name ark-market-data \
  ark-market-data-mcp
```

The server will be available at `http://localhost:8000/sse`.

### Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `WS_URI` | `ws://localhost:9002` | Upstream WebSocket market data endpoint |
| `HTTP_HOST` | `0.0.0.0` | Bind address |
| `HTTP_PORT` | `8000` | Bind port |

### Connect Claude to the HTTP server

Add the running container as an MCP server in Claude's config:

```json
{
  "mcpServers": {
    "ark-market-data": {
      "url": "http://localhost:8000/sse"
    }
  }
}
```

> **Note:** HTTP/SSE transport has higher latency (~100–500 ms per tool call) than stdio (~5–10 ms). Use Docker when you need remote access; use stdio for local, low-latency use.

---

## Development

### Test with MCP Inspector

```bash
# Terminal 1: Start the server
source venv/bin/activate
WS_URI=ws://your-websocket-url.com python3 -m ark_market_data_mcp

# Terminal 2: Open the MCP Inspector
npx @modelcontextprotocol/inspector
```

Open `http://localhost:5173` in your browser to test tools and messages.

### Run tests

```bash
pytest
```

## Architecture

```
┌─────────────────────────┐
│     Claude (User)       │
└────────────┬────────────┘
             │
             │ (via stdio)
             │
┌────────────▼────────────┐
│   MCP Server (Python)   │
│  - Listens on stdio     │
│  - Exposes tools        │
└────────────┬────────────┘
             │
             │ (WebSocket)
             │
┌────────────▼───────────────┐
│   Ark Market Data Server   │
│    (Remote WebSocket)      │
└────────────────────────────┘
```


## Troubleshooting

### Connection Refused

If you see "Connection refused" errors:
- Ensure your WebSocket server is running
- Verify the `WS_URI` environment variable is set correctly
- Check firewall settings if using a remote server

### No Messages Received

- Verify the WebSocket server is sending data in the expected format
- Check the logs: they show all incoming messages
- Use the `get_stream_status` tool to verify connection status

### MCP Tools Not Showing Up

- Restart Claude after adding the MCP
- Check that the server starts without errors
- Verify the MCP was added correctly: `claude mcp list`

## License

MIT

## Author

arkhamides
