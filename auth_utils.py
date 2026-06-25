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
from models import User as UserModel, Ticket as TicketModel
from models import Hotel as HotelModel
from models import UserHotel as UserHotelModel
from models import Team as TeamModel, Category as CategoryModel, SubCategory as SubCategoryModel
from schemas import User
from models import RoleEnum

# Carregar variáveis de ambiente
load_dotenv()

SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = os.getenv("ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 40))

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")

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
        # Decodifica o token JWT usando a chave secreta e o algoritmo definido
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        
        #  Pega o 'sub' do payload, que é o ID do usuário
        user_id: str = payload.get("sub")
        if user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token inválido",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
    except JWTError:
        #  Se o token estiver errado ou expirado, retorna 401
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Busca o usuário no banco usando o ID do token
    user = db.query(UserModel).filter(UserModel.id == int(user_id)).first()
    
    # Se não existir, retorna 401
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuário não encontrado",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Retorna o usuário autenticado
    return user    
    
def create_access_token(user: UserModel, db: Session) -> str:
    now = datetime.now(timezone.utc)
    expire = now + timedelta(minutes=int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES")))

    if user.role in ["admin", "agent"]:
        user_hotels_query = db.query(HotelModel.id, HotelModel.code, HotelModel.name).all()
    else:
        user_hotels_query = (
            db.query(HotelModel.id, HotelModel.code, HotelModel.name)
            .join(UserHotelModel, UserHotelModel.hotel_id == HotelModel.id)
            .filter(UserHotelModel.user_id == user.id)
            .all()
        )

    user_hotels = [
        {"id": h.id, "code": h.code, "name": h.name} for h in user_hotels_query
    ]

    teams = [
        {"id": t.id, "name": t.name}
        for t in db.query(TeamModel.id, TeamModel.name).order_by(TeamModel.id).all()
    ]

    categories = [
        {"id": c.id, "name": c.name, "team_id": c.team_id}
        for c in db.query(CategoryModel.id, CategoryModel.name, CategoryModel.team_id).order_by(CategoryModel.id).all()
    ]

    subcategories = [
        {"id": s.id, "name": s.name, "category_id": s.category_id}
        for s in db.query(SubCategoryModel.id, SubCategoryModel.name, SubCategoryModel.category_id).order_by(SubCategoryModel.id).all()
    ]


    role_menus = {
        "admin": [
            {"label": "Dashboard", "page": "dashboard"},
            {"label": "Chamados", "page": "tickets"},
            {"label": "Qualitor", "page": "qualitor"},
            {"label": "Mural", "page": "mural"},
            {"label": "Equipes", "page": "teams"},
            {"label": "Gerenciar usuários", "page": "manage-users"},
            {"label": "Gerenciar hotéis", "page": "manage-hotels"},
            {"label": "Categorias & SLA", "page": "manage-categories"},
            {"label": "Relatório de Atividades", "page": "activity-report"},
        ],
        "agent": [
            {"label": "Dashboard", "page": "dashboard"},
            {"label": "Chamados", "page": "tickets"},
            {"label": "Qualitor", "page": "qualitor"},
            {"label": "Mural", "page": "mural"},
            {"label": "Equipes", "page": "teams"},
            {"label": "Gerenciar usuários", "page": "manage-users"}
        ],
        "client_manager": [
            {"label": "Meus chamados", "page": "tickets"},
            {"label": "Gerenciar usuários", "page": "manage-users"},
        ],
        "client_receptionist": [
            {"label": "Meus chamados", "page": "tickets"},
        ],
    }

    to_encode = {
        "sub": str(user.id),
        "name": user.name,
        "role": user.role,
        "email": user.email,
        "avatar_url": user.avatar_url or "",
        "iat": now,
        "exp": expire,
        "hotels": user_hotels,
        "teams": teams,
        "categories": categories,
        "subcategories": subcategories,
        "menus": role_menus.get(user.role, [])
    }

    encoded_jwt = jwt.encode(
        to_encode, 
        os.getenv("SECRET_KEY"), 
        algorithm=os.getenv("ALGORITHM", "HS256")
    )

    return encoded_jwt
