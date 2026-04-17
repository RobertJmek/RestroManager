from pydantic_settings import BaseSettings, SettingsConfigDict
import os

# Build the path to the root .env file
env_file_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), ".env")

class Settings(BaseSettings):
    PROJECT_NAME: str = "RestroManager"
    DATABASE_URL: str

    model_config = SettingsConfigDict(env_file=env_file_path, extra="ignore")

settings = Settings()
