"""Entry point for running the MCP server as a module.

Defaults to stdio transport. For HTTP/SSE, use:
    python -m ark_market_data_mcp http
"""

import sys
from .transports import stdio, http


def main():
    """Select transport based on CLI argument or default to stdio."""
    transport = sys.argv[1] if len(sys.argv) > 1 else "stdio"

    if transport == "http":
        http.main()
    elif transport == "stdio":
        stdio.main()
    else:
        print(f"Unknown transport: {transport}")
        print("Usage: python -m ark_market_data_mcp [stdio|http]")
        sys.exit(1)


if __name__ == "__main__":
    main()
