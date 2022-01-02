import asyncio
import json
from typing import List, Tuple, Dict

import aioredis
from aioredis import create_redis_pool
from fastapi import FastAPI
from starlette.websockets import WebSocket, WebSocketDisconnect
from websockets.exceptions import ConnectionClosed

from app.schemas import VoteSchema
from app.settings import settings
from app.websockets import channel

app = FastAPI()

Message = Tuple[bytes, bytes, Dict[bytes, bytes]]

# redis streams >> https://redis.io/topics/streams-intro // https://github.com/elementary-robotics/redisconf-2020-streams-fastapi/blob/master/src/main.py

@app.get("/")
async def root():
    return {"message": "Hello World"}


@app.post("/add-vote", response_model=VoteSchema, status_code=200)
async def add_vote(request: VoteSchema):
    print("---------------------")
    print(settings.redis_url)
    print("---------------------")
    pool = await create_redis_pool(settings.redis_url)

    num_votes = await pool.get(f"{request.user_id}", encoding="utf8")

    if not num_votes:
        await pool.set(f"{request.user_id}", "1")
        num_votes = 1
    else:
        await pool.set(f"{request.user_id}", f"{int(num_votes) + 1}")

    print(f"{int(num_votes) + 1}")

    websockets = await channel.get_connections(str(request.user_id))
    await channel.send_message(f"Votes {request.user_id}: {int(num_votes)}", websockets)

    await pool.xadd("test", {"votes": f"Votes {request.user_id}: {int(num_votes)}"})

    pool.close()
    return request



async def read_from_stream(
    redis: aioredis.Redis, stream: str, latest_id: str = None, past_ms: int = None, last_n: int = None
) -> List[Message]:
    timeout_ms = 60 * 1000

    # Blocking read for every message added after latest_id, using XREAD
    if latest_id is not None:
        return await redis.xread([stream], latest_ids=[latest_id], timeout=timeout_ms)

    # Blocking read for every message added after current timestamp minus past_ms, using XREAD
    if past_ms is not None:
        server_time_s = await redis.time()
        latest_id = str(round(server_time_s * 1000 - past_ms))
        return await redis.xread([stream], latest_ids=[latest_id], timeout=timeout_ms)

    # Non-blocking read for last_n messages, using XREVRANGE
    if last_n is not None:
        messages = await redis.xrevrange(stream, count=last_n)
        return list(reversed([(stream.encode("utf-8"), *m) for m in messages]))

    # Default case, blocking read for all messages added after calling XREAD
    return await redis.xread([stream], timeout=timeout_ms)


@app.websocket("/ws/stream/{stream}")
async def proxy_stream(
    ws: WebSocket,
    stream: str,
    latest_id: str = None,
    past_ms: int = None,
    last_n: int = None,
    max_frequency: float = None,
):
    await ws.accept()
    # Create redis connection with aioredis.create_redis
    redis = await aioredis.create_redis(settings.redis_url)

    # Loop for as long as client is connected and our reads don't time out, sending messages to client over websocket
    while True:
        # Limit max_frequency of messages read by constructing our own latest_id
        to_read_id = latest_id
        if max_frequency is not None and latest_id is not None:
            ms_to_wait = 1000 / (max_frequency or 1)
            ts = int(latest_id.split("-")[0])
            to_read_id = f"{ts + max(0, round(ms_to_wait))}"

        # Call read_from_stream, and return if it raises an exception
        messages: List[Message]
        try:
            messages = await read_from_stream(redis, stream, to_read_id, past_ms, last_n)
        except Exception as e:
            print(f"read timed out for stream {stream}, {e}")
            return

        # If we have no new messages, note that read timed out and return
        if len(messages) == 0:
            print(f"no new messages, read timed out for stream {stream}")
            return

        # If we have max_frequency, assign only most recent message to messages
        if max_frequency is not None:
            messages = messages[-1:]

        # Prepare messages (message_id and JSON-serializable payload dict)
        prepared_messages = []
        for msg in messages:
            latest_id = msg[1].decode("utf-8")
            payload = {k.decode("utf-8"): v.decode("utf-8") for k, v in msg[2].items()}
            prepared_messages.append({"message_id": latest_id, "payload": payload})

        # Send messages to client, handling (ConnectionClosed, WebSocketDisconnect) in case client has disconnected
        try:
            await ws.send_json(prepared_messages)
        except (ConnectionClosed, WebSocketDisconnect):
            print(f"{ws} disconnected from stream {stream}")
            return


@app.websocket("/ws/stream-votes/{user_id}")
async def websocket_endpoint(user_id: int, websocket: WebSocket):
    await channel.connect(str(user_id), websocket)
    websockets = await channel.get_connections(str(user_id))
    try:
        while True:
            data = await websocket.receive_text()
            data = json.loads(data)
            await channel.send_message(data["message"], websockets)
    except (ConnectionClosed, WebSocketDisconnect):
        channel.disconnect(str(user_id), websocket)
