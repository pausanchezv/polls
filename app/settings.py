from os import path

from pydantic import BaseSettings

class Settings(BaseSettings):
    redis_url: str
    postgres_url: str

    class Config:
        env_file = f"{path.dirname(path.dirname(path.abspath(__file__)))}/.env"
        env_file_encoding = 'utf-8'


settings = Settings()

