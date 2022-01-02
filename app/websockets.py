import ast
import json
import pickle
from typing import Dict, Optional, List

from aioredis import create_redis_pool
from starlette.websockets import WebSocket

from app.settings import settings


class WebsocketsChannelBase:
    """
    Websocket channels handler
    """
    def __init__(self) -> None:
        """ WebsocketsChannelsHandler Constructor """
        self.active_connections: Optional[Dict[str, ...]] = None    # Defined by its subclass

    async def connect(self, item_id: str, websocket: WebSocket):
        """ Accepts a websocket connection """
        await websocket.accept()
        try:
            self.active_connections[item_id].append(websocket)
        except KeyError:
            self.active_connections[item_id] = [websocket]

    async def get_connections(self, item_id: str) -> Optional[List[WebSocket]]:
        """ Obtains a specific list of connections """
        try:
            return self.active_connections[item_id]
        except KeyError:
            return None

    def disconnect(self, item_id: str, websocket: WebSocket) -> None:
        """ Deletes a websocket connection """
        if len(self.active_connections[item_id]) == 1:
            del self.active_connections[item_id]
        else:
            self.active_connections[item_id].remove(websocket)

    @staticmethod
    async def send_message(message: str, websockets: Optional[List[WebSocket]]) -> None:
        """ Sends a websocket message """
        if websockets is not None:
            for websocket in websockets:
                await websocket.send_text(message)


class TestChannel(WebsocketsChannelBase):
    """
    Websocket channels cluster-logs
    """
    def __init__(self) -> None:
        """ ClusterLogsChannel Constructor """
        super().__init__()
        self.active_connections: Dict[str, List[WebSocket]] = {}


channel = TestChannel()

