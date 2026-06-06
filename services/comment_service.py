from fastapi import HTTPException, Depends
from sqlalchemy.orm import Session
from datetime import datetime, UTC

from models import Ticket as TicketModel, User as UserModel, TicketComment as CommentModel
from schemas import CommentCreate, ProgressEnum, StatusEnum, RoleEnum

from services.authorization import ensure_user_can_access_ticket

def create_comment_service(
    current_user: UserModel,
    comment: CommentCreate,
    db: Session
):
    ticket = db.query(TicketModel).filter(TicketModel.id == comment.ticket_id).first()
    
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    
    ensure_user_can_access_ticket(ticket, current_user, db)
    
    if ticket.status in [
        StatusEnum.cancelled,
        StatusEnum.closed
    ]:
        raise HTTPException(status_code=403, detail="You can only comment open tickets")
    
    if ticket.progress in [
        ProgressEnum.done, 
        ProgressEnum.awaiting_confirmation, 
        ProgressEnum.waiting
    ]:
        raise HTTPException(status_code=403, detail="You can only comment on tickets that are in progress or with feedback from client status")
  
    db_comment = CommentModel(
        ticket_id=comment.ticket_id,
        user_id=current_user.id,
        comment=comment.comment
    )

    if (
        current_user.role in [RoleEnum.client_manager, RoleEnum.client_receptionist]
        and ticket.progress == ProgressEnum.in_progress
    ):
        ticket.progress = ProgressEnum.feedback
    
    if (
        current_user.role in [RoleEnum.admin, RoleEnum.agent] 
        and ticket.progress == ProgressEnum.feedback
    ):  
        ticket.progress = ProgressEnum.in_progress

    db.add(db_comment)

    ticket.updated_at = datetime.now(UTC)

    db.commit()
    db.refresh(db_comment)

    return db_comment
    