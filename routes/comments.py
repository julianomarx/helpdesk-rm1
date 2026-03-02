from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
import json

from models import TicketComment as CommentModel
from models import User as UserModel
from models import Ticket as TicketModel
from models import RoleEnum

from models import TicketLog as TicketLogModel  
from models import LogActionEnum

from schemas import CommentCreate, Comment as CommentSchema
from schemas import CommentEdit

from database import get_db
from auth_utils import get_current_user

from services.authorization import ensure_user_can_access_ticket

router = APIRouter(
    prefix="/comments",
    tags=["comments"]
)

@router.post("/", response_model=CommentSchema)
def create_comment(
    comment: CommentCreate, db: Session = Depends(get_db), current_user: UserModel = Depends(get_current_user)):
    
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
    
    return db_comment

@router.put("/{comment_id}", response_model=CommentSchema)
def update_comment(
    comment_id: int, 
    updated_data: CommentEdit, 
    db: Session = Depends(get_db), 
    current_user: UserModel = Depends(get_current_user)
):
    db_comment = db.query(CommentModel).filter(CommentModel.id == comment_id).first()
    
    if not db_comment:
        raise HTTPException(status_code=404, detail="Comment not found")
    
    ticket = db.query(TicketModel).filter(TicketModel.id == db_comment.ticket_id).first()
    
    ensure_user_can_access_ticket(ticket, current_user)
    
    # regra: só admin ou dono do comentário pode editar
    if current_user.role != RoleEnum.admin and db_comment.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to edit this comment")
    
    old_value = db_comment.comment
    new_value = updated_data.comment
    
    db_comment.comment = new_value
    
    if old_value != new_value:
    
        log = TicketLogModel(
            ticket_id=ticket.id,
            user_id=current_user.id,
            action=LogActionEnum.comment_updated.value,
            value=json.dumps({
                "old": old_value,
                "new": new_value
            })
        )
        
        db.add(log)

    db.commit()
    db.refresh(db_comment)

    return db_comment

@router.delete("/{comment_id}")
def delete_comment(
    comment_id: int, 
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user)
):
    db_comment = db.query(CommentModel).filter(CommentModel.id == comment_id).first()
    
    if not db_comment:
        raise HTTPException(status_code=404, detail="Comment not fount!")
    
    ticket = db.query(TicketModel).filter(TicketModel.id == db_comment.ticket_id).first()
    
    ensure_user_can_access_ticket(ticket, current_user)
    
    if current_user.role != RoleEnum.admin and db_comment.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="You have no permission to delete this comment")
    
    db.delete(db_comment)
    
    db.commit()
    
    return { "message": f"Comentário: ID {db_comment.id} - Deletado com sucesso." }
