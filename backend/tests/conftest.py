import pytest
from sqlmodel import SQLModel, Session, create_engine
from fastapi.testclient import TestClient
from main import app
from db.session import get_session
from core.security import get_current_guest # Importăm dependența de securitate
from models.user import TokenData

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