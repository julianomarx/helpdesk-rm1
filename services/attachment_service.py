import os
import uuid

from fastapi import UploadFile, HTTPException
from sqlalchemy.orm import Session
from models import User as UserModel
from models import Ticket as TicketModel
from models import Attachment as AttachmentModel

from services.authorization import ensure_user_can_access_ticket

UPLOAD_DIR = "uploads/tickets"

async def save_attachment_service(
    ticket_id: int,
    file: UploadFile,
    current_user: UserModel,
    db: Session
):
    ticket = db.query(TicketModel).filter(TicketModel.id == ticket_id).first()
    
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    
    ensure_user_can_access_ticket(ticket, current_user)
    
    os.makedirs(f"{UPLOAD_DIR}/{ticket.id}", exist_ok=True)
    
    original_name = file.filename
    
    extension = os.path.splitext(original_name)[1]
    
    stored_name = f"{uuid.uuid4()}{extension}"
    
    file_path = f"{UPLOAD_DIR}/{ticket.id}/{stored_name}"
    
    with open(file_path, "wb") as buffer:
        buffer.write(await file.read())
        
    file_size = os.path.getsize(file_path)
    
    attachment = AttachmentModel(
        ticket_id=ticket_id,
        file_name=original_name,
        stored_name=stored_name,
        mime_type=file.content_type,
        file_size=file_size,
        uploaded_by=current_user.id   
    )
    
    db.add(attachment)
    db.commit()
    
    db.refresh(attachment)
    
    return attachment