import bcrypt
import jwt
from datetime import datetime, timedelta, timezone
from typing import Optional, List
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlmodel import Session, select

from core.config import settings
from db.session import get_session
from models.user import User, TokenData, UserRole

# Configurare OAuth2
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/auth/login")

# OAuth2 scheme for optional authentication (no 401 for missing header)
oauth2_scheme_optional = OAuth2PasswordBearer(tokenUrl="api/auth/login", auto_error=False)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))

def get_password_hash(password: str) -> str:
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt

async def get_current_user(
    token: str = Depends(oauth2_scheme),
    session: Session = Depends(get_session)
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Nu s-au putut valida datele de acces",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
        token_data = TokenData(email=email, role=payload.get("role"))
    except jwt.PyJWTError:
        raise credentials_exception
    
    user = session.exec(select(User).where(User.email == token_data.email)).first()
    if user is None:
        raise credentials_exception
    return user

def require_role(allowed_roles: List[str]):
    """
    Dependency pentru a verifica rolul utilizatorului autentificat.
    Ex: require_role(["Waiter", "Manager"])
    """
    def role_checker(current_user: User = Depends(get_current_user)):
        if current_user.role.value not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Nu aveți permisiunea necesară pentru această acțiune"
            )
        return current_user
    return role_checker

async def get_current_user_optional(
    token: Optional[str] = Depends(oauth2_scheme_optional),
    session: Session = Depends(get_session)
) -> Optional[User]:
    """
    Dependency for optional authentication.
    Returns the user if authenticated, None if no token provided.
    Raises 401 for invalid/malformed tokens.
    """
    # No token provided - this is OK for optional auth
    if token is None:
        return None
    
    # Token provided but invalid - raise 401
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid authentication credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
    except jwt.PyJWTError:
        raise credentials_exception
    
    user = session.exec(select(User).where(User.email == email)).first()
    if user is None:
        raise credentials_exception
        
    return user


async def get_valid_user_or_guest(
    token: Optional[str] = Depends(oauth2_scheme_optional)
) -> Optional[TokenData]:
    """
    Validates token as either a Guest token or a valid User token.
    Returns TokenData with role info, or raises 401 if token is invalid.
    Used for endpoints that accept both guests and authenticated users.
    """
    if token is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid authentication credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        role: str = payload.get("role")
        
        if role is None:
            raise credentials_exception
            
        # Accept Guest tokens
        if role == "Guest":
            table_id: int = payload.get("table_id")
            if table_id is None:
                raise credentials_exception
            return TokenData(role=role, table_id=table_id)
        
        # Accept valid User tokens (any role)
        email: str = payload.get("sub")
        user_id: int = payload.get("user_id")
        if email is None or user_id is None:
            raise credentials_exception
            
        return TokenData(email=email, role=role, user_id=user_id)
        
    except jwt.PyJWTError:
        raise credentials_exception


async def get_current_guest(token: str = Depends(oauth2_scheme)) -> TokenData:
    """
    Dependency special pentru GUEST (Clienti la masa).
    Extrage table_id direct din token pentru a preveni falsificarea.
    """
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        role: str = payload.get("role")
        table_id: int = payload.get("table_id")
        
        if role != "Guest" or table_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token-ul de Guest este invalid"
            )
        return TokenData(role=role, table_id=table_id)
    except jwt.PyJWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Nu s-a putut valida token-ul de Guest"
        )
