from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session
from db.session import get_session
from core.security import get_current_user
from models.user import User, UserUpdate, UserRead

router = APIRouter(prefix="/users", tags=["Users"])

@router.get("/me", response_model=UserRead)
async def read_user_me(current_user: User = Depends(get_current_user)):
    """
    Returnează datele profilului pentru utilizatorul curent logat.
    """
    return current_user

@router.put("/me", response_model=UserRead)
async def update_user_me(
    user_update: UserUpdate,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """
    Actualizează detaliile utilizatorului curent (ex: nume, telefon).
    Nu permite modificarea rolului sau a statusului de activitate.
    """
    # Folosim dict pentru compatibilitate cu Pydantic v1/v2
    user_data = user_update.dict(exclude_unset=True)
    
    for key, value in user_data.items():
        # Securitate: Ignorăm câmpurile care țin de administrare sau identificare
        if key not in ["role", "is_active", "hashed_password", "email"]:
            setattr(current_user, key, value)
            
    try:
        session.add(current_user)
        session.commit()
        session.refresh(current_user)
    except Exception as e:
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A apărut o eroare la salvarea datelor. Poate numărul de telefon este deja folosit."
        )
        
    return current_user
