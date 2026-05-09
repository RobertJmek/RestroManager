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

    # DeepSeek API Configuration
    # Models: deepseek-v4-flash | deepseek-v4-pro | deepseek-chat (deprecated 2026/07/24)
    # Base URL: https://api.deepseek.com (OpenAI-compatible)
    DEEPSEEK_API_KEY: str | None = None
    DEEPSEEK_MODEL: str = "deepseek-v4-flash"
    DEEPSEEK_BASE_URL: str = "https://api.deepseek.com"
    USE_AI_RECOMMENDATIONS: bool = True

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
