import pytest
from fastapi.testclient import TestClient
from unittest.mock import MagicMock
from sqlmodel import Session

import sys
import os

# Setăm variabile de mediu pentru testare (evităm validările din config.py pe medii de test)
os.environ["SECRET_KEY"] = "this_is_a_test_secret_key_that_is_long_enough_for_pydantic"
os.environ["DATABASE_URL"] = "postgresql+psycopg2://user:pass@localhost:5432/testdb"

# Adăugăm folderul backend în PYTHONPATH pentru a asigura importurile corecte
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from main import app
from db.session import get_session

@pytest.fixture
def mock_db_session():
    """
    Fixture care generează o sesiune de bază de date (SQLModel) simulată.
    Aceasta previne orice apel real către baza de date.
    """
    mock_session = MagicMock(spec=Session)
    yield mock_session

@pytest.fixture
def client(mock_db_session):
    """
    Fixture care generează un TestClient FastAPI.
    Suprascrie dependența de bază de date (get_session) cu mock-ul.
    """
    def override_get_session():
        yield mock_db_session

    app.dependency_overrides[get_session] = override_get_session
    
    with TestClient(app) as c:
        yield c
        
    # Curățăm suprascrierile după terminarea testului
    app.dependency_overrides.clear()
