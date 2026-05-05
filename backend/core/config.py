from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import field_validator
import os

# Build the path to the root .env file
env_file_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), ".env")

DEFAULT_KEYS = {"secret", "changeme", "your-secret-key-here", "test", ""}

class Settings(BaseSettings):
    PROJECT_NAME: str = "RestroManager"
    DATABASE_URL: str
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    @field_validator("SECRET_KEY")
    @classmethod
    def validate_secret_key(cls, v: str) -> str:
        if not v or len(v) < 32:
            raise ValueError("SECRET_KEY must be at least 32 characters")
        if v in DEFAULT_KEYS:
            raise ValueError("SECRET_KEY must not be a known default/placeholder value")
        return v

    model_config = SettingsConfigDict(env_file=env_file_path, extra="ignore")

settings = Settings()
