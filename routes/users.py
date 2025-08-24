from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from passlib.context import CryptContext

from models import User as UserModel
from schemas import User, UserCreate, UserUpdate
from database import get_db

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

router = APIRouter(
    prefix="/users",
    tags=["users"]
)

@router.post("/", response_model=User)
def create_user(user: UserCreate, db: Session = Depends(get_db)):
    db_user = UserModel(
        name=user.name,
        email=user.email,
        password_hash=pwd_context.hash(user.password),
        role=user.role
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

@router.get("/", response_model=List[User])
def list_users(db: Session = Depends(get_db)):
    users = db.query(UserModel).all()
    return users

@router.get("/{user_id}", response_model=User)
def get_user(user_id: int, db: Session = Depends(get_db)):
    user = db.query(UserModel).filter(UserModel.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found!")
    return user

@router.put("/{user_id}", response_model=User)
def update_user(user_id: int, user_update: UserUpdate, db: Session = Depends(get_db)):
    user = db.query(UserModel).filter(UserModel.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")

    data = user_update.model_dump(exclude_unset=True)

    # Se enviar senha, transforma em hash antes de atualizar
    if "password" in data:
        data["password_hash"] = pwd_context.hash(data.pop("password"))

    # Atualiza os campos do usuário
    for field, value in data.items():
        setattr(user, field, value)

    db.commit()
    db.refresh(user)
    return user

@router.delete("/{user_id}")
def delete_user(user_id: int, db: Session = Depends(get_db)):
    user = db.query(UserModel).filter(UserModel.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")
    db.delete(user)
    db.commit()
    return { "message": f"Usuário {user_id} - {user.name} - foi deletado com sucesso." }
