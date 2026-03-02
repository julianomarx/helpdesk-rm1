from fastapi import HTTPException, Depends
from sqlalchemy.orm import Session

from models import Ticket as TicketModel, User as UserModel, TicketComment as CommentModel
from schemas import CommentCreate 

from services.authorization import ensure_user_can_access_ticket

def create_comment_service(
    current_user: UserModel,
    comment: CommentCreate,
    db: Session
):
    ticket = db.query(TicketModel).filter(TicketModel.id == comment.ticket_id).first()
    
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    
    ensure_user_can_access_ticket(ticket, current_user)

    db_comment = CommentModel(
        ticket_id=comment.ticket_id,
        user_id=current_user.id,
        comment=comment.comment
    )
    
    db.add(db_comment)
    db.commit()
    db.refresh(db_comment)
    