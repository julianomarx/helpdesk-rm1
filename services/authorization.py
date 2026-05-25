from fastapi import HTTPException, Depends
from models import User as UserModel, Ticket as TicketModel, UserHotel as UserHotelModel, UserTeam as UserTeamModel
from models import Hotel as HotelModel
from models import RoleEnum 

from auth_utils import get_current_user

from sqlalchemy.orm import Session

def ensure_can_assign_agent(
    ticket: TicketModel,
    current_user: UserModel,
    target_user: UserModel,
    db: Session
):
    if current_user.role == RoleEnum.admin:
        return
    
    if current_user.role in [
        RoleEnum.client_manager,
        RoleEnum.client_receptionist
    ]:
        raise HTTPException(status_code=403, detail="Você não tem permissão para atribuir agentes")
    
    if current_user.role == RoleEnum.agent:
        if target_user.id == current_user.id:
            return
        
    if (
        ticket.assigned_team
        and any(
            ut.team_id == ticket.assigned_team_id
            for ut in target_user.teams
        )
    ):
        return
    
    raise HTTPException(status_code=403, detail="Agente não pode atribuir o ticket à alguém fora do seu time")

def ensure_user_can_access_ticket(
    ticket: TicketModel,
    user: UserModel,
    db: Session
) -> None:
    if user.role == RoleEnum.admin:
        return

    accessible_hotel_ids = get_user_accessible_hotel_ids(
        user.id,
        db
    )

    if ticket.hotel_id not in accessible_hotel_ids:
        raise HTTPException(
            status_code=403,
            detail="You don't have access to this ticket"
        )

    if user.role == RoleEnum.agent:
        user_team_ids = get_user_accessible_team_ids(
            user.id,
            db
        )

        if ticket.assigned_team_id not in user_team_ids:
            raise HTTPException(
                status_code=403,
                detail="You don't have access to this ticket"
            )
        
def ensure_user_can_access_hotel(user: UserModel, hotel: HotelModel) -> None:
    if user.role == RoleEnum.admin:
        return
    
    accessible_hotel_ids = get_user_accessible_hotel_ids(user)
    
    if hotel.id not in accessible_hotel_ids:
        raise HTTPException(status_code=403, detail="You dont have access to this hotel")
    
def ensure_admin(current_user: UserModel = Depends(get_current_user)) -> UserModel:
    if current_user.role != RoleEnum.admin:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    return current_user

def get_user_accessible_hotel_ids(
    user_id: int,
    db: Session
) -> set[int]:
    rows = (
        db.query(UserHotelModel.hotel_id)
        .filter(UserHotelModel.user_id == user_id)
        .all()
    )

    return {hotel_id for (hotel_id,) in rows}

def get_user_accessible_team_ids(
    user_id: int,
    db: Session
) -> set[int]:
    rows = (
        db.query(UserTeamModel.team_id)
        .filter(UserTeamModel.user_id == user_id)
        .all()
    )

    return {team_id for (team_id,) in rows}