import aioredis
from aioredis import create_redis_pool
from fastapi import FastAPI, Depends
from sqlalchemy.exc import NoResultFound
from sqlalchemy.orm import Session
from starlette.websockets import WebSocket

from app.db.db import Base, engine, get_db
from app.models import Counter
from app.schemas import VoteSchema
from app.settings import settings
from app.websockets import TestChannel

Base.metadata.create_all(engine)

app = FastAPI()



# redis streams >> https://redis.io/topics/streams-intro // https://github.com/elementary-robotics/redisconf-2020-streams-fastapi/blob/master/src/main.py

@app.get("/")
async def root():
    return {"message": "Hello World"}


async def save_to_postgres(slug: str, db: Session) -> int:
    try:
        counter = db.query(Counter).filter(Counter.slug == slug).one()
    except NoResultFound:
        counter = Counter(slug=slug, count=1)
        db.add(counter)
    else:
        counter.count += 1
    finally:
        db.commit()

    return counter.count


@app.post("/add-vote", response_model=int, status_code=200)
async def add_vote(request: VoteSchema, db: Session = Depends(get_db)):
    pool = await create_redis_pool(settings.redis_url)

    votenum = request.user_id[-1]

    num_votes = await pool.get(f"{votenum}", encoding="utf8")

    if not num_votes:
        await pool.set(f"{votenum}", "1")
        num_votes = 1
    else:
        await pool.set(f"{votenum}", f"{int(num_votes) + 1}")

    print(f"{int(num_votes) + 1}")

    postgres_counter = await save_to_postgres(request.user_id, db)

    await TestChannel.push(f"channels:counter:{request.user_id}", pool, num_votes)

    pool.close()
    return postgres_counter


@app.websocket("/ws/stream/{slug}")
async def proxy_stream(ws: WebSocket, slug: str):
    channel = TestChannel(await aioredis.create_redis_pool(settings.redis_url), slug)
    await channel.connect(ws)


