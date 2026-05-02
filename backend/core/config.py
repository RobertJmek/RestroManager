from pydantic_settings import BaseSettings, SettingsConfigDict
import os

# Build the path to the root .env file
env_file_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), ".env")

class Settings(BaseSettings):
    PROJECT_NAME: str = "RestroManager"
    DATABASE_URL: str
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    model_config = SettingsConfigDict(env_file=env_file_path, extra="ignore")

settings = Settings()
