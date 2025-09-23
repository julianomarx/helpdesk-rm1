# auth.py
import os
from datetime import datetime, timezone, timedelta
from typing import Optional

from dotenv import load_dotenv
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from database import get_db
from models import User as UserModel
from schemas import User

# Carregar variáveis de ambiente
load_dotenv()

SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = os.getenv("ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 60))

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

#funcoes de hash
def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

#funcoes de autenticacao
def authenticate_user(db: Session, email: str, password: str) -> Optional[UserModel]:
    user = db.query(UserModel).filter(UserModel.email == email).first()
    if not user:
        return None
    if not verify_password(password, user.password_hash):
        return None
    return user

def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    try:
        # 1️⃣ Decodifica o token JWT usando a chave secreta e o algoritmo definido
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        
        # 2️⃣ Pega o 'sub' do payload, que é o ID do usuário
        user_id: str = payload.get("sub")
        if user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token inválido",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
    except JWTError:
        # 3️⃣ Se o token estiver errado ou expirado, retorna 401
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # 4️⃣ Busca o usuário no banco usando o ID do token
    user = db.query(UserModel).filter(UserModel.id == int(user_id)).first()
    
    # 5️⃣ Se não existir, retorna 401
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuário não encontrado",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # 6️⃣ Retorna o usuário autenticado
    return user    
    
def create_access_token(user: UserModel) -> str:
    now = datetime.now(timezone.utc)
    expire = now + timedelta(minutes=int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES")))

    user_hotels = [
    {"id": uh.hotel.id, "code": uh.hotel.code, "name": uh.hotel.name}
    for uh in user.hotels
    ]
    
    role_menus = {
        "admin": [
            {"label": "Dashboard", "page": "dashboard"},
            {"label": "Usuários", "page": "users"},
            {"label": "Criar Usuário", "page": "create-user"},
            {"label": "Chamados", "page": "tickets"},
            {"label": "Abrir chamado", "page": "create-ticket"}
        ],
        "agent": [
            {"label": "Chamados", "page": "tickets"},
        ],
        "client_manager": [
            {"label": "Dashboard", "page": "dashboard"},
            {"label": "Abrir chamado", "page": "create-ticket"},
            {"label": "Meus chamados", "page": "tickets"},
            {"label": "Gerenciar usuários", "page": "users"},
        ],
        "client_receptionist": [
            {"label": "Abrir chamado", "page": "create-ticket"},
            {"label": "Meus chamados", "page": "tickets"},
        ],
    }

    to_encode = {
        "sub": str(user.id),
        "role": user.role,
        "email": user.email,
        "iat": now,
        "exp": expire,
        "hotels": user_hotels,
        "menus": role_menus.get(user.role, [])
    }

    encoded_jwt = jwt.encode(
        to_encode, 
        os.getenv("SECRET_KEY"), 
        algorithm=os.getenv("ALGORITHM", "HS256")
    )

    return encoded_jwt