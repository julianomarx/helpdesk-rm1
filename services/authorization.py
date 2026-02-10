from fastapi import HTTPException
from models import User as UserModel, Ticket as TicketModel
from models import Team as TeamModel
from models import RoleEnum 
from services.permissions import validate_field_permission

from sqlalchemy.orm import Session

def ensure_can_assign_agent(
    ticket: TicketModel,
    current_user: UserModel,
    tager_user: UserModel,
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
        if tager_user.id == current_user.id:
            return
        
    if (
        ticket.assigned_team
        and any(
            ut.team_id == ticket.assigned_team_id
            for ut in tager_user.teams
        )
    ):
        return
    
    raise HTTPException(status_code=403, detail="Agente não pode atribuir o ticket à alguém fora do seu time")

def ensure_can_manage_team_members(current_user: UserModel, team: TeamModel, target_user: UserModel):
    
    if current_user.role != RoleEnum.admin:
        raise HTTPException(status_code=403, detail="Apenas administradores podem remover ou adicionar membros às equipes")