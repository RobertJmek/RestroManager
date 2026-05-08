import pytest
from pydantic_core._pydantic_core import ValidationError
from core.config import Settings

def test_config_valid_secret():
    # Should not raise exception
    settings = Settings(DATABASE_URL="testdb", SECRET_KEY="valid_secret_key_that_is_at_least_32_chars")
    assert settings.SECRET_KEY == "valid_secret_key_that_is_at_least_32_chars"

def test_config_invalid_secret_length():
    with pytest.raises(ValidationError) as exc_info:
        Settings(DATABASE_URL="testdb", SECRET_KEY="too_short")
        
    assert "SECRET_KEY must be at least 32 characters" in str(exc_info.value)

def test_config_invalid_secret_default():
    with pytest.raises(ValidationError) as exc_info:
        # Pydantic won't allow default values to pass the custom validator
        Settings(DATABASE_URL="testdb", SECRET_KEY="your-secret-key-here")
        
    assert "SECRET_KEY must be at least 32 characters" in str(exc_info.value)
