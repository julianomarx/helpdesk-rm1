from fastapi import HTTPException

from models import TicketLog as TicketLogModel, LogActionEnum
from models import Ticket as TicketModel, User as UserModel

from models import ProgressEnum

from services.authorization import ensure_can_assign_agent

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
            detail="Usuário não pertence à equipe responsável pelo ticket. Verifique se o usuário está vinculado À esta equipe"
        )
        
def start_ticket_service(
    ticket_id: int,
    current_user: UserModel,
    db: Session
):
    ticket = db.query(TicketModel).filter(TicketModel.id == ticket_id).with_for_update().first()
    
    if not ticket: 
        raise HTTPException(status_code=404, detail="Ticket não localizado")
    
    ensure_can_assign_agent(ticket, current_user, current_user, db)
    ensure_agent_belongs_to_ticket_assigned_team(ticket, current_user)
    
    if ticket.assigned_to is not None:
        raise HTTPException(status_code=400, detail="This ticket is already being handled by another user")
    
    ticket.assigned_to = current_user.id
    ticket.progress = ProgressEnum.in_progress.value
    
    log = TicketLogModel(
        ticket_id=ticket.id,
        user_id=current_user.id,
        action=LogActionEnum.ticket_started.value,
        value=None,
    )
    
    db.add(log)
    
    db.commit()
    
    db.refresh(ticket)
    
    return ticket