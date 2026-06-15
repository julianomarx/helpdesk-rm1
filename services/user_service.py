from math import ceil
from fastapi import Depends, HTTPException
from models import User as UserModel, UserHotel as UserHotelModel, UserTeam as UserTeamModel, Hotel as HotelModel
from schemas import UserHotelsUpdate, UserCreate, UserUpdate, UserTeamsUpdate
from models import RoleEnum

from services.validations import ensure_hotels_exist, ensure_teams_exist

from sqlalchemy import or_
from sqlalchemy.exc import IntegrityError
from passlib.context import CryptContext

from services.validations import ensure_hotels_exist
from services.authorization import get_user_accessible_hotel_ids

from sqlalchemy.orm import Session, selectinload

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def create_user_service(
    new_user: UserCreate, 
    db: Session,
    current_user: UserModel
    ):
    
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
        hotel_ids = list(set(new_user.hotel_ids))

        ensure_hotels_exist(hotel_ids, db)

        db.bulk_insert_mappings(
            UserHotelModel,
            [
                {
                    "user_id": created_user.id,
                    "hotel_id": hid
                }
                for hid in hotel_ids
            ]
        )

    if new_user.team_ids:
        team_ids = list(set(new_user.team_ids))

        ensure_teams_exist(team_ids, db)

        db.bulk_insert_mappings(
            UserTeamModel,
            [
                {
                    "user_id": created_user.id,
                    "team_id": tid
                }
                for tid in team_ids
            ]
        )
    
    db.commit()
    db.refresh(created_user)

    return created_user

def update_user_hotels_service(
    target_user_id: int,
    hotels_update: UserHotelsUpdate,
    current_user: UserModel,
    db: Session
):
    target_user = (
        db.query(UserModel)
        .filter(UserModel.id == target_user_id)
        .first()
    )

    if not target_user:
        raise HTTPException(status_code=404, detail="User not found")

    if current_user.role in [RoleEnum.agent, RoleEnum.client_receptionist]:
        raise HTTPException(
            status_code=403,
            detail="You dont have permission to update user hotels"
        )

    hotel_ids = set(hotels_update.hotel_ids)

    ensure_hotels_exist(hotel_ids, db)

    # -----------------------------
    # REGRAS DE PERMISSÃO
    # -----------------------------
    if current_user.role == RoleEnum.client_manager:

        if target_user.role != RoleEnum.client_receptionist:
            raise HTTPException(
                status_code=403,
                detail="Manager can only manage hotels access of receptionists"
            )

        manager_hotel_ids = {uh.hotel_id for uh in current_user.hotels}
        invalid_assignments = hotel_ids - manager_hotel_ids

        if invalid_assignments:
            raise HTTPException(
                status_code=403,
                detail=f"You cant assign hotels you dont manage: {list(invalid_assignments)}"
            )


    current_hotel_ids = {
        hotel_id
        for (hotel_id,) in (
            db.query(UserHotelModel.hotel_id)
            .filter(UserHotelModel.user_id == target_user.id)
            .all()
        )
    }

    to_add_ids = hotel_ids - current_hotel_ids
    to_remove_ids = current_hotel_ids - hotel_ids

    # remove só o que saiu
    if to_remove_ids:
        db.query(UserHotelModel).filter(
            UserHotelModel.user_id == target_user.id,
            UserHotelModel.hotel_id.in_(to_remove_ids)
        ).delete(synchronize_session=False)

    # adiciona só o que entrou
    if to_add_ids:
        db.bulk_insert_mappings(
            UserHotelModel,
            [
                {
                    "user_id": target_user.id,
                    "hotel_id": hotel_id
                }
                for hotel_id in to_add_ids
            ]
        )

    db.flush()

def update_user_teams_service(
    target_user_id: int, 
    teams_update: UserTeamsUpdate, 
    db: Session,
    current_user: UserModel
):
    target_user = (
        db.query(UserModel)
        .filter(UserModel.id == target_user_id)
        .first()
    )

    if not target_user:
        raise HTTPException(status_code=404, detail="User not found")
    
    team_ids = teams_update.team_ids

    ensure_teams_exist(team_ids, db)

    db.query(UserTeamModel).filter(UserTeamModel.user_id == target_user.id).delete()

    for team_id in team_ids:
        db.add(UserTeamModel(
            user_id=target_user.id,
            team_id=team_id
        ))

    db.flush()

    
def list_users_service(
    db: Session,
    current_user: UserModel,

    *,
    page: int = 1,
    page_size: int = 5,

    hotel_id: int | None = None,
    role: RoleEnum | None = None,
    search: str | None = None
):

    query = (
        db.query(UserModel)
        .options(

            selectinload(
                UserModel.hotels
            ),

            selectinload(
                UserModel.teams
            )
        )
    )

    if current_user.role == RoleEnum.admin:

        pass

    elif current_user.role == RoleEnum.agent:

        accessible_hotels = (
            get_user_accessible_hotel_ids(
                current_user.id,
                db
            )
        )

        query = query.filter(
            UserModel.hotels.any(
                UserHotelModel.hotel_id.in_(accessible_hotels)
            )
        )

        query = query.filter(
            UserModel.role.in_(
                [
                    RoleEnum.client_manager,
                    RoleEnum.client_receptionist
                ]
            )
        )

    elif current_user.role == RoleEnum.client_manager:

        accessible_hotels = get_user_accessible_hotel_ids(
            current_user.id,
            db
        )

        query = query.filter(
            UserModel.hotels.any(
                UserHotelModel.hotel_id.in_(accessible_hotels)
            )
        )

        query = query.filter(
            UserModel.role == RoleEnum.client_receptionist
        )

    else:

        raise HTTPException(
            status_code=403,
            detail="Not allowed"
        )

    if hotel_id:

        query = query.filter(

            UserModel.hotels.any(
                HotelModel.id == hotel_id
            )

        )

    if role:

        query = query.filter(
            UserModel.role == role
        )

    if search:

        search = search.strip()

        query = query.filter(

            or_(

                UserModel.name.ilike(
                    f"%{search}%"
                ),

                UserModel.email.ilike(
                    f"%{search}%"
                )

            )
        )
        

    total = query.count()

    query = query.order_by(
        UserModel.name.asc()
    )

    query = query.offset(
        (page - 1) * page_size
    ).limit(
        page_size
    )

    users = query.all()

    return {

        "items": users,

        "total": total,

        "page": page,

        "page_size": page_size,

        "pages": ceil(
            total / page_size
        ) if total else 0
    }

def get_user_service(
    current_user: UserModel,
    target_user_id: int,
    db: Session
):
    target_user = (
        db.query(UserModel)
        .options(
            selectinload(UserModel.hotels)
            .selectinload(UserHotelModel.hotel),

            selectinload(UserModel.teams)
            .selectinload(UserTeamModel.team)
        )
        .filter(UserModel.id == target_user_id)
        .first()
    )

    if not target_user: 
        raise HTTPException(status_code=404, detail="User not found")
     
    if current_user.role == RoleEnum.admin:
        return target_user
     
    if current_user.role == RoleEnum.client_receptionist:
        raise HTTPException(status_code=403, detail="User not found")
    
    accessible_hotels = get_user_accessible_hotel_ids(current_user.id, db)
    
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
        
        return (
            db.query(UserModel)
            .options(
                selectinload(UserModel.hotels)
                .selectinload(UserHotelModel.hotel),

                selectinload(UserModel.teams)
                .selectinload(UserTeamModel.team)
            )
            .filter(UserModel.id == target_user.id)
            .first()
        )
    
    raise HTTPException(status_code=403, detail="User not found")
        
def update_user_service(
    target_user_id: int,
    current_user: UserModel,
    user_update: UserUpdate,
    db: Session
):
    target_user = (
        db.query(UserModel)
        .options(
            selectinload(UserModel.hotels)
            .selectinload(UserHotelModel.hotel),

            selectinload(UserModel.teams)
            .selectinload(UserTeamModel.team)
        )
        .filter(UserModel.id == target_user_id)
        .first()
    )
    
    if not target_user:
        raise HTTPException(status_code=404, detail="User not found")
    
    if current_user.role == RoleEnum.admin:
        pass
    
    elif current_user.role == RoleEnum.client_manager:
        
        acessible_hotels = get_user_accessible_hotel_ids(current_user.id, db)
        
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

def delete_user_service(
    target_user_id: int,
    current_user: UserModel,
    db: Session
):
    
    user = db.query(UserModel).filter(UserModel.id == target_user_id).first()
    
    if not user: 
        raise HTTPException(status_code=404, detail="User not found")
    
    db.delete(user)
    
    db.commit()