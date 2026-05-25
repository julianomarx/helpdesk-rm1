from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List
from passlib.context import CryptContext

from models import User as UserModel, UserHotel as UserHotelModel
from schemas import User, UserUpdate, UserCreateWithHotels, UserHotelsUpdate, UserOut, UserTeamsUpdate
from models import RoleEnum
from database import get_db
from auth_utils import get_current_user

from services.user_service import create_user_service, update_user_hotels_service, list_users_service, get_user_service, update_user_service, delete_user_service, update_user_teams_service
from services.authorization import ensure_admin

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
    created_user = create_user_service(user, db, current_user)
    
    db.commit()
    db.refresh(created_user)
        
    return created_user
    
@router.get("/", response_model=List[User])
def list_users(
    hotel_id: int | None = Query(default=None),
    role: RoleEnum | None = Query(default=None),
    search: str | None = Query(default=None),
    db: Session = Depends(get_db), 
    current_user: UserModel = Depends(get_current_user)
):
    return list_users_service(db,current_user, hotel_id, role, search)
    
@router.get("/{user_id}", response_model=UserOut)
def get_user(
    user_id: int, 
    db: Session = Depends(get_db), 
    current_user: UserModel = Depends(get_current_user)
):
    
    user = get_user_service(current_user, user_id, db)
    
    return {
        "id": user.id,
        "name": user.name,
        "email": user.email,
        "role": user.role,
        "hotels": [
            {
                "id": uh.hotel.id,
                "code": uh.hotel.code,
                "name": uh.hotel.name
            }
            for uh in user.hotels
        ],
        "teams": [
            {
                "id": ut.team.id,
                "name": ut.team.name
            }
            for ut in user.teams
        ]
    }

@router.put("/{user_id}", response_model=User)
def update_user(
    user_id: int, 
    user_update: UserUpdate, 
    db: Session = Depends(get_db), 
    current_user: UserModel = Depends(get_current_user)
):
    user = update_user_service(user_id, current_user, user_update, db)
    
    db.commit()
    db.refresh(user)
    
    return user

@router.delete("/{user_id}")
def delete_user(
    user_id: int, 
    db: Session = Depends(get_db), 
    current_user: UserModel = Depends(ensure_admin)):
    
    
    delete_user_service(user_id, current_user, db)
    
    return { "message": f"Usuário {user_id} - foi deletado com sucesso." }

@router.put("/{user_id}/hotels")
def update_user_hotels(
    user_id: int,
    hotels_update: UserHotelsUpdate,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user)):
    
    user = update_user_hotels_service(user_id, hotels_update, current_user, db)
    
    db.commit()

    return {"message": "ok"}

@router.put("/{user_id}/teams")
def update_user_teams(
    user_id: int,
    teams_update: UserTeamsUpdate,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(ensure_admin)
):
    user = update_user_teams_service(user_id, teams_update, db, current_user)

    db.commit()

    return {"message" : "ok"}

    