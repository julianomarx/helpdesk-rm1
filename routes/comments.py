from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from models import TicketComment as CommentModel
from models import User as UserModel
from schemas import CommentCreate, Comment as CommentSchema
from database import get_db
from auth_utils import get_current_user

router = APIRouter(
    prefix="/comments",
    tags=["comments"]
)

@router.post("/", response_model=CommentSchema)
def create_comment(comment: CommentCreate, db: Session = Depends(get_db), current_user: UserModel = Depends(get_current_user)):
    db_comment = CommentModel(
        ticket_id=comment.ticket_id,
        user_id=comment.user_id,
        comment=comment.comment
    )
    db.add(db_comment)
    db.commit()
    db.refresh(db_comment)
    return db_comment

@router.get("/", response_model=List[CommentSchema])
def list_comments(db: Session = Depends(get_db), current_user: UserModel = Depends(get_current_user)):
    comments = db.query(CommentModel).all()
    return comments

@router.get("/{comment_id}", response_model=CommentSchema)
def get_comment(comment_id: int, db: Session = Depends(get_db), current_user: UserModel = Depends(get_current_user)):
    comment = db.query(CommentModel).filter(CommentModel.id == comment_id).first()
    if not comment:
        raise HTTPException(status_code=404, detail="Comment not found")
    return comment

