from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from database import get_db
from auth_utils import get_current_user

from services.authorization import ensure_user_can_access_ticket

from typing import List

from models import TicketLog as TicketLogModel, Ticket as TicketModel
from models import User as UserModel
from schemas import TicketLogOut

router = APIRouter(
    prefix="/ticket-logs",
    tags=["ticket-logs"]
)

@router.get("/{ticket_id}", response_model=List[TicketLogOut])
def list_ticket_logs(
    ticket_id: int,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user)
):
    ticket = db.query(TicketModel).filter(TicketModel.id == ticket_id).first()
    if not ticket:
        raise HTTPException(
            status_code=404, 
            detail="Ticket não encontrado"
        )
        
    ensure_user_can_access_ticket(ticket, current_user)
    
    logs = (
        db.query(TicketLogModel)
        .filter(TicketLogModel.ticket_id == ticket_id)
        .order_by(TicketLogModel.created_at.asc())
        .all()
    )
    
    return logs
