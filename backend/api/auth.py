from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlmodel import Session, select
from datetime import timedelta

from db.session import get_session
from models.user import User, UserCreate, UserRead, Token
from models.table import Table
from core.security import get_password_hash, verify_password, create_access_token, settings

router = APIRouter(prefix="/auth", tags=["Authentication"])

@router.post("/register", response_model=UserRead, status_code=status.HTTP_201_CREATED)
async def register(user_in: UserCreate, session: Session = Depends(get_session)):
    """
    Înregistrează un utilizator nou (Waiter, Chef, Manager).
    """
    # Verificăm dacă email-ul există deja
    existing_user = session.exec(select(User).where(User.email == user_in.email)).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Acest email este deja înregistrat"
        )
    
    # Verificăm dacă numărul de telefon există deja
    existing_phone = session.exec(select(User).where(User.phone == user_in.phone)).first()
    if existing_phone:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Acest număr de telefon este deja înregistrat"
        )

    db_user = User(
        name=user_in.name,
        email=user_in.email,
        phone=user_in.phone,
        role=user_in.role,
        hashed_password=get_password_hash(user_in.password)
    )
    
    session.add(db_user)
    session.commit()
    session.refresh(db_user)
    return db_user

@router.post("/login", response_model=Token)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    session: Session = Depends(get_session)
):
    """
    Autentifică un utilizator și returnează un token JWT.
    """
    user = session.exec(select(User).where(User.email == form_data.username)).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email sau parolă incorectă",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Contul este dezactivat"
        )

    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={
            "sub": user.email,
            "role": user.role.value,  # garantăm că e string, ex: "Manager"
            "user_id": user.id,
            "name": user.name,
        },
        expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

@router.post("/guest-login/{table_number}", response_model=Token)
async def guest_login(table_number: int, session: Session = Depends(get_session)):
    """
    Generare token pentru Guest pe baza scanării QR la masă.
    Verifică că masa există în baza de date înainte de a emite token-ul.
    """
    table = session.exec(select(Table).where(Table.number == table_number)).first()
    if not table:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Masa {table_number} nu există"
        )

    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"role": "Guest", "table_id": table_number},
        expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}
