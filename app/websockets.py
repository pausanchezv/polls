import ast
import json
import pickle
from typing import Dict, Optional, List, Tuple

import aioredis
from aioredis import create_redis_pool
from starlette.websockets import WebSocket, WebSocketDisconnect
from websockets.exceptions import ConnectionClosed

from app.settings import settings

Message = Tuple[bytes, bytes, Dict[bytes, bytes]]


class WebsocketsChannelBase:
    """
    Websocket channels handler
    """
    def __init__(self, redis, key: str, prefix: str) -> None:
        """ WebsocketsChannelsHandler Constructor """
        self.redis = redis
        self.key = key
        self.prefix = prefix

    async def connect(self, websocket: WebSocket):
        """ Accepts a websocket connection """
        await websocket.accept()

        latest_id = None

        while True:
            try:
                messages: List[Message] = await self.read_from_stream(latest_id)
            except Exception as e:
                print(f"read timed out for stream {self.prefix}:{self.key}, {e}")
                return

            prepared_messages = []
            for msg in messages:
                latest_id = msg[1].decode("utf-8")
                payload = {k.decode("utf-8"): v.decode("utf-8") for k, v in msg[2].items()}
                prepared_messages.append({"message_id": latest_id, "payload": payload})

            # Send messages to client, handling (ConnectionClosed, WebSocketDisconnect) in case client has disconnected
            try:
                for message in prepared_messages:
                    await websocket.send_json(message)
            except (ConnectionClosed, WebSocketDisconnect):
                print(f"{websocket} disconnected from stream {self.prefix}:{self.key}")
                return

    async def read_from_stream(self, latest_id: str = None) -> List[Message]:
        timeout_ms = 60 * 1000

        if latest_id is not None:
            return await self.redis.xread([f"{self.prefix}:{self.key}"], latest_ids=[latest_id], timeout=timeout_ms)

        return await self.redis.xread([f"{self.prefix}:{self.key}"], timeout=timeout_ms)

    @staticmethod
    async def push(channel_name, redis, num_votes):
        message = await redis.xadd(f"{channel_name}", {"votes": f"Votes {channel_name}: {int(num_votes)}"})
        await redis.xdel(f"{channel_name}", message)


class TestChannel(WebsocketsChannelBase):
    """
    Websocket channels cluster-logs
    """

    def __init__(self, redis, key: str) -> None:
        """ WebsocketsChannelsHandler Constructor """
        super().__init__(redis, key, "channels:counter")


