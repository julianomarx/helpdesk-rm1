from fastapi import Depends, HTTPException
from models import User as UserModel, UserHotel as UserHotelModel
from schemas import UserHotelsUpdate
from models import RoleEnum

from services.validations import ensure_hotels_exist

from sqlalchemy.orm import Session

def update_user_hotels_service(
    target_user_id: int,
    hotels_update: UserHotelsUpdate,
    current_user: UserModel,
    db: Session
):
    
    target_user = db.query(UserModel).filter(UserModel.id == target_user_id).first()
    if not target_user:
        raise HTTPException(status_code=404, detail="User not found")
    
    if current_user.role in [ RoleEnum.agent, RoleEnum.client_receptionist ]:
        raise HTTPException(status_code=403, detail="You dont have permission to update user hotels")
    
    hotel_ids = hotels_update.hotel_ids
    ensure_hotels_exist(hotel_ids, db)
    
    #Ver se o current_user tem permissão pra atribuir algum hotel ao target_user via role 
    if current_user.role == RoleEnum.client_manager:
        
        if target_user.role != RoleEnum.client_receptionist:
            raise HTTPException(status_code=403, detail="Manager can only manage hotels access of receptionists")
        
        manager_hotel_ids = {
            uh.hotel_id for uh in current_user.hotels
        }
        
        invalid_assignments = set(hotel_ids) - manager_hotel_ids
        
        if invalid_assignments:
            raise HTTPException(status_code=403, detail=f"You cant assign hotels you dont manage: {list(invalid_assignments)}")
        
    db.query(UserHotelModel).filter(UserHotelModel.user_id == target_user.id).delete()
    
    for hotel_id in hotel_ids:
        db.add(UserHotelModel(
            user_id=target_user.id,
            hotel_id=hotel_id
        ))
        
    return target_user
    