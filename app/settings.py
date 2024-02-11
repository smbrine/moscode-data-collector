from dotenv import load_dotenv
from pydantic_settings import BaseSettings

load_dotenv()


class Settings(BaseSettings):
    KAFKA_URL: str
    POSTGRES_URL: str
    DEBUG: bool = False
    REDIS_URL: str
    LISTEN_ADDR: str
    LISTEN_PORT: int
    SECRET_KEY: str

    class Config:
        env_file = ".env"
