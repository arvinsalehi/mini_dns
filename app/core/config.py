from pydantic_settings import BaseSettings, SettingsConfigDict
import os

class Settings(BaseSettings):
    MONGODB_URI: str = os.getenv("MONGODB_URI", "mongodb://mongo:27017")
    MONGODB_DB: str = os.getenv("MONGODB_DB", "testdb")
    DEBUG: int = os.getenv("DEBUG", 0)

    model_config = SettingsConfigDict(env_file=".env")

settings = Settings()
