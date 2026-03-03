import asyncio
import json
import websockets

from .config import WS_URI, SUBSCRIBE_MSG, MAX_BUFFER_SIZE, logger
from .state import MarketState


async def connect_and_stream(state: MarketState) -> None:
    """Background task: maintains WebSocket connection to C++ server and buffers incoming data."""
    try:
        while True:
            try:
                logger.info(f"Connecting to C++ WebSocket at {WS_URI}...")
                async with websockets.connect(WS_URI) as ws:
                    state.ws_connection = ws
                    logger.info("Connected. Subscribing to market data...")
                    await ws.send(json.dumps(SUBSCRIBE_MSG, separators=(",", ":")))
                    logger.info(f"Sent subscribe message: {SUBSCRIBE_MSG}")
                    logger.info("Waiting for messages...")

                    message_count = 0
                    async for raw_message in ws:
                        message_count += 1
                        logger.info(f"[Message #{message_count}] Received: {raw_message[:100]}...")

                        try:
                            parsed = json.loads(raw_message)
                        except json.JSONDecodeError:
                            logger.warning(f"Failed to parse message: {raw_message[:100]}")
                            parsed = {"raw": raw_message}

                        state.add_message(raw_message, parsed, MAX_BUFFER_SIZE)

                        # Check alerts after every new message
                        triggered = state.alert_manager.check(list(state.buffer))
                        for alert in triggered:
                            logger.info(f"[ALERT TRIGGERED] {alert}")

            except (websockets.exceptions.ConnectionClosed, ConnectionRefusedError, OSError) as e:
                logger.warning(f"WebSocket error: {e}. Reconnecting in 3s...")
                state.ws_connection = None
                await asyncio.sleep(3)
            except Exception as e:
                logger.error(f"Unexpected error in WebSocket task: {e}. Reconnecting in 5s...")
                state.ws_connection = None
                await asyncio.sleep(5)
    except asyncio.CancelledError:
        logger.info("WebSocket streaming task cancelled")
        state.ws_connection = None
    except Exception as e:
        logger.error(f"Fatal error in connect_and_stream: {e}")
        state.ws_connection = None
