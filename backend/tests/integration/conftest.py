import pytest
from sqlmodel import Session

from core.security import create_access_token, get_password_hash
from models.user import User, UserRole

# Hash precomputat o singură dată la import (bcrypt e lent);
# parola nu este folosită la login în aceste teste.
_TEST_PASSWORD_HASH = get_password_hash("TestPassword123!")


def _staff_headers(session: Session, name: str, email: str, phone: str, role: UserRole) -> dict:
    """Creează un utilizator de staff în DB-ul de test și emite un JWT real pentru el."""
    user = User(
        name=name,
        email=email,
        phone=phone,
        role=role,
        hashed_password=_TEST_PASSWORD_HASH,
        is_active=True,
    )
    session.add(user)
    session.commit()
    session.refresh(user)

    # Același payload ca în api/auth.py:login — exersăm calea reală de auth.
    token = create_access_token(
        data={"sub": user.email, "role": user.role.value, "user_id": user.id, "name": user.name}
    )
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def chef_headers(session: Session) -> dict:
    return _staff_headers(session, "Chef Test", "chef@test.com", "+40700000001", UserRole.chef)


@pytest.fixture
def waiter_headers(session: Session) -> dict:
    return _staff_headers(session, "Waiter Test", "waiter@test.com", "+40700000002", UserRole.waiter)
