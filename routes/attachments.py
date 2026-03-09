from fastapi import APIRouter, UploadFile, File, Depends, HTTPException
from sqlalchemy.orm import Session

from models import User as UserModel, Ticket as TicketModel
from models import Attachment as AttachmentModel
from schemas import AttachmentOut, UserOut

from database import get_db
from services.attachment_service import save_attachment_service
from services.authorization import ensure_user_can_access_ticket

from auth_utils import get_db, get_current_user

router = APIRouter(prefix="/tickets", tags=["attachments"])

@router.post("/{ticket_id}/attachments", response_model=AttachmentOut)
async def upload_attachment(
    file: UploadFile,
    ticket_id: int,
    current_user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    attachment = await save_attachment_service(ticket_id, file, current_user, db)
    
    return {
        "id": attachment.id,
        "file_name": attachment.file_name,
        "mime_type": attachment.mime_type,
        "file_size": attachment.file_size,
        "created_at": attachment.created_at,
        "url": f"/uploads/{attachment.stored_name}",
        "uploader": attachment.uploader
    }

@router.get("/{ticket_id}/attachments", response_model=list[AttachmentOut])
def list_attachments(
    ticket_id: int, 
    current_user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    ticket = db.query(TicketModel).filter(TicketModel.id == ticket_id).first()
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    
    ensure_user_can_access_ticket(ticket, current_user)

    attachments = db.query(AttachmentModel).filter(
        AttachmentModel.ticket_id == ticket_id
    ).all()

    # Transformar para Pydantic e gerar URL
    result = []
    for a in attachments:
        result.append(
            AttachmentOut(
                id=a.id,
                file_name=a.file_name,
                mime_type=a.mime_type,
                file_size=a.file_size,
                created_at=a.created_at,
                url=f"/uploads/{a.stored_name}",  # ou como você realmente serve os arquivos
                uploader=UserOut.from_orm(a.uploader),  # converter uploader para Pydantic
            )
        )

    return result