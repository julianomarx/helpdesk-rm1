from fastapi import HTTPException

from models import TicketLog as TicketLogModel, LogActionEnum
from models import Ticket as TicketModel, User as UserModel

from sqlalchemy.orm import Session

def assign_agent_to_ticket(ticket: TicketModel, current_user: UserModel, target_user: UserModel, db: Session):
    old_agent = ticket.assigned_to
    
    ticket.assigned_to = target_user.id
    
    log = TicketLogModel(
        ticket_id=ticket.id,
        user_id=current_user.id,
        action=LogActionEnum.assigned_changed.value,
        value=str(target_user.id)
    )
    
    db.add(log)
    
    
def ensure_agent_belongs_to_ticket_assigned_team(ticket: TicketModel, target_user: UserModel):
    
    if not ticket.assigned_team_id:
        raise HTTPException(status_code=400, detail="Ticket não possui equipe atribuida")
    
    belongs_to_team = any(
        ut.team_id == ticket.assigned_team_id
        for ut in target_user.teams
    )

    if not belongs_to_team:
        raise HTTPException(
            status_code=400,
            detail="Usuário não pertence à equipe responsável pelo ticket. Use o endpoint de transferência de equipe"
        )