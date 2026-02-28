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
git clone https://github.com/arkhamides/ark-market-data-mcp.git
cd ark-market-data-mcp
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -e .
```

## Quick Start

### 1. Set up your WebSocket endpoint

The MCP server connects to a WebSocket at `ws://localhost:9002` by default, but you can override this:

```bash
export WS_URI=ws://your-websocket-url.com
```

### 2. Add to Claude

```bash
export WS_URI=ws://your-websocket-url.com
claude mcp add ark-market-data ark-market-data-mcp
```

### 3. Use with Claude

```bash
claude chat
```

Ask Claude to use the market data tools, e.g., "What's the latest market data?"

## Configuration

### Environment Variables

- `WS_URI` - WebSocket server URL (default: `ws://localhost:9002`)

Example with ngrok:

```bash
export WS_URI=wss://abc123.ngrok.io
```

Example with Cloudflare Tunnel:

```bash
export WS_URI=wss://your-domain.cloudflare.dev
```

## Available Tools

The MCP server exposes the following tools for Claude:

- **`get_latest_message`** - Get the most recent market message from the stream
- **`get_recent_messages`** - Get the last N messages (default: 10, max: 500)
- **`get_stream_status`** - Check WebSocket connection status and buffer statistics
- **`clear_buffer`** - Clear the message buffer

## Development

### Run the server locally

```bash
source venv/bin/activate
WS_URI=wss://your-url python3 -m ark_market_data_mcp
```

### Test with MCP Inspector

```bash
# Terminal 1: Start the server
source venv/bin/activate
WS_URI=wss://your-url python3 -m ark_market_data_mcp

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
┌────────────▼────────────┐
│  Market Data Server     │
│  (Remote WebSocket)     │
└─────────────────────────┘
```

## Deployment Options

### Local WebSocket with ngrok

For testing with a local WebSocket server exposed publicly:

```bash
# Terminal 1: Start your local WebSocket server (on port 9002)
# ...your server...

# Terminal 2: Expose with ngrok
ngrok tcp 9002
# Note the URL: tcp://...

# Terminal 3: Add to Claude
export WS_URI=wss://7.tcp.eu.ngrok.io:10542
claude mcp add ark-market-data ark-market-data-mcp
```

### Cloudflare Tunnel (Recommended)

For a stable, free alternative to ngrok:

```bash
# Terminal 1: Start your local WebSocket server (on port 9002)
# ...your server...

# Terminal 2: Create a Cloudflare Tunnel
cloudflare tunnel run ark-market-data
# Get your stable URL from the output

# Terminal 3: Add to Claude
export WS_URI=wss://your-domain.cloudflare.dev
claude mcp add ark-market-data ark-market-data-mcp
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
