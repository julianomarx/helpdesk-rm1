from fastapi import HTTPException, Depends
from models import User as UserModel, Ticket as TicketModel
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

def ensure_user_can_access_ticket(ticket: TicketModel, user: UserModel) -> bool:
    if user.role == RoleEnum.admin:
        return True

    if user.role == RoleEnum.agent:
        user_team_ids = {ut.team_id for ut in user.teams}
        user_hotel_ids = {uh.hotel_id for uh in user.hotels}
        return (ticket.assigned_team_id in user_team_ids) and (ticket.hotel_id in user_hotel_ids)

    if user.role in [RoleEnum.client_manager, RoleEnum.client_receptionist]:
        user_hotel_ids = {uh.hotel_id for uh in user.hotels}
        return ticket.hotel_id in user_hotel_ids

    return False

def ensure_admin(current_user: UserModel = Depends(get_current_user)) -> UserModel:
    if current_user.role != RoleEnum.admin:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    return current_user