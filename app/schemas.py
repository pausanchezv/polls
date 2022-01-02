from pydantic import BaseModel


class VoteSchema(BaseModel):
    user_id: str

    class Config:
        orm_mode = True

