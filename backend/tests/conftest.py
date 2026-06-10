import os
import pytest
from unittest.mock import MagicMock
from sqlmodel import SQLModel, Session, create_engine
from fastapi.testclient import TestClient
from main import app
from db.session import get_session
from core.security import get_current_guest, get_valid_user_or_guest
from core.limiter import limiter
from models.user import TokenData


def pytest_collection_modifyitems(config, items):
    """Marchează automat testele unit/integration după directorul în care se află,
    ca `pytest -m unit` / `-m integration` să funcționeze. tests/evals/ rămâne nemarcat."""
    for item in items:
        test_path = str(item.fspath)
        if f"{os.sep}unit{os.sep}" in test_path:
            item.add_marker(pytest.mark.unit)
        elif f"{os.sep}integration{os.sep}" in test_path:
            item.add_marker(pytest.mark.integration)


@pytest.fixture(autouse=True)
def _disable_rate_limiting():
    """Dezactivează rate limiting-ul în teste (TestClient folosește un singur IP)."""
    limiter.enabled = False
    yield
    limiter.enabled = True

# Baza de date de test (SQLite)
TEST_DATABASE_URL = "sqlite:///./test.db"
engine_test = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})

@pytest.fixture(name="session")
def session_fixture():
    SQLModel.metadata.create_all(engine_test)
    with Session(engine_test) as session:
        yield session
    SQLModel.metadata.drop_all(engine_test)

@pytest.fixture(name="client")
def client_fixture(session: Session):
    # 1. Override pentru Baza de Date
    app.dependency_overrides[get_session] = lambda: session
    
    # 2. Override pentru Autentificare (Mock Guest)
    # Simulăm un Guest care stă la Masa nr. 1
    def mock_get_current_guest():
        return TokenData(username="guest_test", role="guest", table_id=1)
    
    app.dependency_overrides[get_current_guest] = mock_get_current_guest

    client = TestClient(app)
    yield client
    
    # Curățăm după test
    app.dependency_overrides.clear()


@pytest.fixture
def mock_db_session():
    """Mock SQLModel session for unit tests — no real DB hit."""
    mock = MagicMock(spec=Session)
    app.dependency_overrides[get_session] = lambda: mock
    yield mock
    app.dependency_overrides.pop(get_session, None)


@pytest.fixture
def mock_guest_auth():
    """Override get_valid_user_or_guest to mock guest authentication."""
    def mock_get_valid_user_or_guest():
        return TokenData(role="Guest", table_id=1)
    
    app.dependency_overrides[get_valid_user_or_guest] = mock_get_valid_user_or_guest
    yield
    app.dependency_overrides.pop(get_valid_user_or_guest, None)
