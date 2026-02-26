from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List
from passlib.context import CryptContext

from models import User as UserModel, UserHotel as UserHotelModel
from schemas import User, UserUpdate, UserCreateWithHotels, UserHotelsUpdate, UserOut
from models import RoleEnum
from database import get_db
from auth_utils import get_current_user

from services.user_service import create_user_service, update_user_hotels_service, list_users_service, get_user_service


pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

router = APIRouter(
    prefix="/users",
    tags=["users"]
)

@router.post("/", response_model=User)
def create_user(
    user: UserCreateWithHotels, 
    db: Session = Depends(get_db), 
    current_user: UserModel = Depends(get_current_user)
):
    created_user = create_user_service(user, current_user, db)
    
    db.commit()
    db.refresh(created_user)
        
    return created_user
    
@router.get("/", response_model=List[User])
def list_users(
    hotel_id: int | None = Query(default=None),
    role: int | None = Query(default=None),
    db: Session = Depends(get_db), 
    current_user: UserModel = Depends(get_current_user)
):
    return list_users_service(db,current_user, hotel_id, role)
    
@router.get("/{user_id}", response_model=User)
def get_user(
    user_id: int, 
    db: Session = Depends(get_db), 
    current_user: UserModel = Depends(get_current_user)
):
    
    return get_user_service(current_user, user_id, db)

@router.put("/{user_id}", response_model=User)
def update_user(user_id: int, user_update: UserUpdate, db: Session = Depends(get_db), current_user: UserModel = Depends(get_current_user)):
    user = db.query(UserModel).filter(UserModel.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")
    data = user_update.model_dump(exclude_unset=True)

    if data["name"] == user.name:
        data.pop("name") 

    if data["email"] == user.email: 
        data.pop("email")
    else:
        existing_user =  db.query(UserModel).filter(UserModel.email == data["email"]).first()
        if existing_user and existing_user.id != user.id: 
            raise HTTPException(status_code=400, detail="Email já está em uso por outro usuário")
        
    if "password" in data:
        if pwd_context.verify(data["password"], user.password_hash):
            data.pop("password") 
    
    else: 
        data["password_hash"] = pwd_context.hash(data.pop("password"))

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

@router.put("/{user_id}/hotels", response_model=UserOut)
def update_user_hotels(user_id: int, hotels_update: UserHotelsUpdate, db: Session = Depends(get_db), current_user: UserModel = Depends(get_current_user)):
    
    user = update_user_hotels_service(user_id, hotels_update, current_user, db)
    
    db.commit()
    db.refresh(user)
    
    return user