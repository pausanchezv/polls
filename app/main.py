import json

from aioredis import create_redis_pool
from fastapi import FastAPI
from starlette.websockets import WebSocket, WebSocketDisconnect

from app.schemas import VoteSchema
from app.settings import settings
from app.websockets import channel

app = FastAPI()


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

    pool.close()
    return request


@app.websocket("/ws/stream-votes/{user_id}")
async def websocket_endpoint(user_id: int, websocket: WebSocket):
    await channel.connect(str(user_id), websocket)
    websockets = await channel.get_connections(str(user_id))
    try:
        while True:
            data = await websocket.receive_text()
            data = json.loads(data)
            await channel.send_message(data["message"], websockets)
    except WebSocketDisconnect:
        channel.disconnect(str(user_id), websocket)
