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
from app.websockets import TestChannel

app = FastAPI()



# redis streams >> https://redis.io/topics/streams-intro // https://github.com/elementary-robotics/redisconf-2020-streams-fastapi/blob/master/src/main.py

@app.get("/")
async def root():
    return {"message": "Hello World"}


@app.post("/add-vote", response_model=VoteSchema, status_code=200)
async def add_vote(request: VoteSchema):
    # print("---------------------")
    # print(settings.redis_url)
    # print("---------------------")
    pool = await create_redis_pool(settings.redis_url)

    votenum = request.user_id[-1]

    num_votes = await pool.get(f"{votenum}", encoding="utf8")

    if not num_votes:
        await pool.set(f"{votenum}", "1")
        num_votes = 1
    else:
        await pool.set(f"{votenum}", f"{int(num_votes) + 1}")

    print(f"{int(num_votes) + 1}")

    # websockets = await channel.get_connections(str(request.user_id))
    # await channel.send_message(f"Votes {request.user_id}: {int(num_votes)}", websockets)

    await TestChannel.push(f"channels:counter:{request.user_id}", pool, num_votes)

    pool.close()
    return request


@app.websocket("/ws/stream/{slug}")
async def proxy_stream(ws: WebSocket, slug: str):
    channel = TestChannel(await aioredis.create_redis_pool(settings.redis_url), slug)
    await channel.connect(ws)


