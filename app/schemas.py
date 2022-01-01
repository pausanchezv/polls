from pydantic import BaseModel


class VoteSchema(BaseModel):
    user_id: int

    class Config:
        orm_mode = True

