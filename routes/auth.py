# routes/auth.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from fastapi.security import OAuth2PasswordRequestForm

from database import get_db
from models import User as UserModel
from auth_utils import create_access_token, verify_password, get_current_user  # funções auxiliares
from schemas import Token
from schemas import User

router = APIRouter(
    prefix="/auth",
    tags=["auth"]
)

@router.post("/login", response_model=Token)
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    # Busca o usuário no banco
    user = db.query(UserModel).filter(UserModel.email == form_data.username).first()

    # Verifica se o usuário existe
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuário e/ou senha inválidos"
        )

    # Verifica a senha
    if not verify_password(form_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuário e/ou senha inválidos",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Cria o token com expiração fixa (do .env)
    access_token = create_access_token(user)

    return {
        "access_token": access_token,
        "token_type": "bearer"
    }

@router.get("/me", response_model=User)
def read_current_user(current_user: UserModel = Depends(get_current_user)):
    return current_user
    
@router.post("/refresh", response_model=Token)
def refresh_token(current_user: UserModel = Depends(get_current_user)):
    new_token = create_access_token(current_user)
    return {
        "access_token": new_token,
        "token_type": "bearer"
    }