from fastapi import Depends, HTTPException
from models import User as UserModel, UserHotel as UserHotelModel
from schemas import UserHotelsUpdate, UserCreateWithHotels, UserUpdate
from models import RoleEnum

from services.validations import ensure_hotels_exist

from sqlalchemy.exc import IntegrityError
from passlib.context import CryptContext

from services.validations import ensure_hotels_exist
from services.authorization import get_user_accessible_hotel_ids

from sqlalchemy.orm import Session

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def create_user_service(
    new_user: UserCreateWithHotels, 
    current_user: UserModel, 
    db: Session ):
    
    if current_user.role in [RoleEnum.agent, RoleEnum.client_receptionist]:
        raise HTTPException(status_code=403, detail="Your user dont have permission to create another user")
    
    if current_user.role == RoleEnum.client_manager:
        if new_user.role != RoleEnum.client_receptionist:
            raise HTTPException(status_code=403, detail="Client managers can only create receptionists")
        
    existing_user = db.query(UserModel).filter(UserModel.email == new_user.email).first()
    
    if existing_user:
        raise HTTPException(status_code=403, detail="Email already registered for another user")
    
    created_user = UserModel(
        name=new_user.name,
        email=new_user.email,
        password_hash=pwd_context.hash(new_user.password),
        role=new_user.role
    )
    
    db.add(created_user)
    db.flush()
    
    if new_user.hotel_ids:
        ensure_hotels_exist(new_user.hotel_ids, db)
        
        for hid in set(new_user.hotel_ids):
            db.add(UserHotelModel(
                user_id=created_user.id,
                hotel_id=hid
            ))
            
    
    db.commit()
    db.refresh(created_user)

    return created_user

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

def list_users_service(
    db: Session,
    current_user: UserModel,
    hotel_id: int | None = None,
    role: RoleEnum |None = None
):
    
    query = db.query(UserModel)
    
    #admin
    if current_user.role == RoleEnum.admin:
        if hotel_id:      
            query = query.join(UserHotelModel).filter(
                UserHotelModel.hotel_id == hotel_id
            )
        
        if role:
            query = query.filter(UserModel.role == role)
            
        return query.distinct().all()
        
    #agent 
    elif current_user.role == RoleEnum.agent:
        if not hotel_id:
            raise HTTPException(status_code=400, detail="Agents must provide hotel_id to get users")
        
        accessible_hotels = get_user_accessible_hotel_ids(current_user)

        if hotel_id not in accessible_hotels:
            raise HTTPException(status_code=403, detail="You dont have access to this hotel")
        
        query = query.join(UserHotelModel).filter(
            UserHotelModel.hotel_id == hotel_id
        )
        
        query = query.filter(UserModel.role != RoleEnum.admin)
        
        if role:
            if role == RoleEnum.admin:
                return []   
             
            query = query.filter(UserModel.role == role)
            
        return query.distinct().all()
        
    elif current_user.role == RoleEnum.client_manager:
        
        accessible_hotels = get_user_accessible_hotel_ids(current_user)
        
        query = query.join(UserHotelModel).filter(
            UserHotelModel.hotel_id.in_(accessible_hotels)
        )   
        
        
        if hotel_id:
            if hotel_id not in accessible_hotels:
                raise HTTPException(status_code=403, detail="Not allowed for this hotel")
            
            query = query.filter(UserHotelModel.hotel_id == hotel_id)
            
        allowed_roles = [
            RoleEnum.client_manager,
            RoleEnum.client_receptionist
        ]
        
        query = query.filter(UserModel.role.in_(allowed_roles))
        
        if role:
            if role not in allowed_roles:
                return []
            
            query = query.filter(UserModel.role == role)
            
        return query.distinct().all()
        
        
    #receptionist 
    elif current_user.role == RoleEnum.client_receptionist:
        raise HTTPException(status_code=403, detail="Receptionists should not list users")
    
    else:
        raise HTTPException(status_code=403, detail="Not allowed")
    
def get_user_service(
    current_user: UserModel,
    target_user_id: int,
    db: Session
):
    target_user = db.query(UserModel).filter(UserModel.id == target_user_id).first()

    if not target_user: 
        raise HTTPException(status_code=404, detail="User not found")
     
    if current_user.role == RoleEnum.admin:
        return target_user
     
    if current_user.role == RoleEnum.client_receptionist:
        raise HTTPException(status_code=403, detail="User not found")
    
    accessible_hotels = get_user_accessible_hotel_ids(current_user)
    
    if not any(
        uh.hotel_id in accessible_hotels
        for uh in target_user.hotels
    ):
        raise HTTPException(status_code=403, detail="User not found")

    if current_user.role == RoleEnum.agent: 
        if target_user.role == RoleEnum.admin:
            raise HTTPException(status_code=403, detail="User not found")
        
        return target_user
    
    if current_user.role == RoleEnum.client_manager:
        accessible_roles = [
            RoleEnum.client_manager, RoleEnum.client_receptionist
        ]
        
        if target_user.role not in accessible_roles:
            raise HTTPException(status_code=403, detail="User not found")
        
        return target_user
    
    raise HTTPException(status_code=403, detail="User not found")
        
def update_user_service(
    target_user_id: int,
    current_user: UserModel,
    user_update: UserUpdate,
    db: Session
):
    target_user = db.query(UserModel).filter(UserModel.id == target_user_id).first()
    
    if not target_user:
        raise HTTPException(status_code=404, detail="User not found")
    
    if current_user.role == RoleEnum.admin:
        pass
    
    elif current_user.role == RoleEnum.client_manager:
        
        acessible_hotels = get_user_accessible_hotel_ids(current_user)
        
        if not any(
            uh.hotel_id in acessible_hotels
            for uh in target_user.hotels
        ):
            raise HTTPException(status_code=404, detail="User not found")
        
        allowed_roles = [
            RoleEnum.client_manager,
            RoleEnum.client_receptionist
        ]
        
        if target_user.role not in allowed_roles:
            raise HTTPException(status_code=404, detail="User not found")
        
    else:
        raise HTTPException(status_code=404, detail="User not found")
    
    update_fields = user_update.model_dump(exclude_unset=True)
    
    if "name" in update_fields and update_fields["name"] == target_user.name:
        update_fields.pop("name")
        
    if "email" in update_fields:
        if update_fields["email"] == target_user.email:
            update_fields.pop("email")
        else:
            existing_user = db.query(UserModel).filter(UserModel.email == update_fields["email"]).first()
            
            if existing_user and existing_user.id != target_user.id:
                raise HTTPException(status_code=400, detail="Email already in use")
            
    if "password" in update_fields:
        if pwd_context.verify(update_fields["password"], target_user.password_hash):
            update_fields.pop("password")
        else:
            update_fields["password_hash"] = pwd_context.hash(update_fields.pop("password"))
            
    for field_to_update, field_value in update_fields.items():
        setattr(target_user, field_to_update, field_value)
        
    return target_user