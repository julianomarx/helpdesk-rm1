from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from passlib.context import CryptContext
from sqlalchemy.exc import IntegrityError

from models import User as UserModel
from schemas import User, UserCreate, UserUpdate
from database import get_db
from auth_utils import get_current_user

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

router = APIRouter(
    prefix="/users",
    tags=["users"]
)

@router.post("/", response_model=User)
def create_user(user: UserCreate, db: Session = Depends(get_db)):
    existing_user = db.query(UserModel).filter(UserModel.email == user.email).first()

    if existing_user:
        raise HTTPException(status_code=400, detail="Email já está em uso")

    db_user = UserModel(
        name=user.name,
        email=user.email,
        password_hash=pwd_context.hash(user.password),
        role=user.role
    )
    db.add(db_user)

    try:
        db.commit()
        db.refresh(db_user)

    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="Email Já cadastrado")
    return db_user

@router.get("/", response_model=List[User])
def list_users(db: Session = Depends(get_db), current_user: UserModel = Depends(get_current_user)):
    users = db.query(UserModel).all()
    return users

@router.get("/{user_id}", response_model=User)
def get_user(user_id: int, db: Session = Depends(get_db), current_user: UserModel = Depends(get_current_user)):
    user = db.query(UserModel).filter(UserModel.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuário Não encontrado")
    return user

@router.put("/{user_id}", response_model=User)
def update_user(user_id: int, user_update: UserUpdate, db: Session = Depends(get_db), current_user: UserModel = Depends(get_current_user)):
    user = db.query(UserModel).filter(UserModel.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")
    data = user_update.model_dump(exclude_unset=True)

    if data["name"] == user.name:
        data.pop("name") #Mesmo nome não atualiza

    if data["email"] == user.email: #se passar um email idgual ao usuário selecionado por parametro não irá atualizar o email
        data.pop("email")
    else:
        existing_user =  db.query(UserModel).filter(UserModel.email == data["email"]).first()
        if existing_user and existing_user.id != user.id: ##email ja em uso por outro usuário, não atualiza
            raise HTTPException(status_code=400, detail="Email já está em uso por outro usuário")
        
    # Se enviar senha, transforma em hash antes de atualizar
    if "password" in data:
        if pwd_context.verify(data["password"], user.password_hash):
            data.pop("password") #mesma senha, não atualiza
    
    else: #atualiza a senha se cair no else
        data["password_hash"] = pwd_context.hash(data.pop("password"))

    # Atualiza os campos do usuário
    for field, value in data.items():
        setattr(user, field, value)
    db.commit()
    db.refresh(user)
    return user

@router.delete("/{user_id}")
def delete_user(user_id: int, db: Session = Depends(get_db), current_user: UserModel = Depends(get_current_user)):
    user = db.query(UserModel).filter(UserModel.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")
    db.delete(user)
    db.commit()
    return { "message": f"Usuário {user_id} - {user.name} - foi deletado com sucesso." }
