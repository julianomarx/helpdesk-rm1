import os
from fastapi import APIRouter, UploadFile, File, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from models import User as UserModel, Ticket as TicketModel, Attachment as AttachmentModel
from models import RoleEnum
from schemas import AttachmentOut

from database import get_db
from services.attachment_service import save_attachment_service
from services.authorization import ensure_user_can_access_ticket
from auth_utils import get_current_user

router = APIRouter(prefix="/tickets", tags=["attachments"])

UPLOAD_DIR = "uploads/tickets"


def _attachment_url(attachment: AttachmentModel) -> str:
    return f"/api/tickets/{attachment.ticket_id}/attachments/{attachment.id}/download"


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
        "url": _attachment_url(attachment),
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
        raise HTTPException(status_code=404, detail="Ticket não encontrado")

    ensure_user_can_access_ticket(ticket, current_user, db)

    attachments = (
        db.query(AttachmentModel)
        .filter(AttachmentModel.ticket_id == ticket_id)
        .order_by(AttachmentModel.created_at.desc())
        .all()
    )

    return [
        AttachmentOut(
            id=a.id,
            file_name=a.file_name,
            mime_type=a.mime_type,
            file_size=a.file_size,
            created_at=a.created_at,
            url=_attachment_url(a),
            uploader=a.uploader,
        )
        for a in attachments
    ]


@router.get("/{ticket_id}/attachments/{attachment_id}/download")
def download_attachment(
    ticket_id: int,
    attachment_id: int,
    current_user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    ticket = db.query(TicketModel).filter(TicketModel.id == ticket_id).first()
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket não encontrado")

    ensure_user_can_access_ticket(ticket, current_user, db)

    attachment = (
        db.query(AttachmentModel)
        .filter(
            AttachmentModel.id == attachment_id,
            AttachmentModel.ticket_id == ticket_id
        )
        .first()
    )
    if not attachment:
        raise HTTPException(status_code=404, detail="Anexo não encontrado")

    file_path = os.path.abspath(
        os.path.join(UPLOAD_DIR, str(ticket_id), attachment.stored_name)
    )
    uploads_root = os.path.abspath(UPLOAD_DIR)
    if not file_path.startswith(uploads_root + os.sep):
        raise HTTPException(status_code=403, detail="Acesso negado")

    if not os.path.isfile(file_path):
        raise HTTPException(status_code=404, detail="Arquivo não encontrado no servidor")

    return FileResponse(
        path=file_path,
        filename=attachment.file_name,
        media_type=attachment.mime_type or "application/octet-stream"
    )


@router.delete("/{ticket_id}/attachments/{attachment_id}")
def delete_attachment(
    ticket_id: int,
    attachment_id: int,
    current_user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    attachment = (
        db.query(AttachmentModel)
        .filter(
            AttachmentModel.id == attachment_id,
            AttachmentModel.ticket_id == ticket_id
        )
        .first()
    )
    if not attachment:
        raise HTTPException(status_code=404, detail="Anexo não encontrado")

    if current_user.role != RoleEnum.admin and attachment.uploaded_by != current_user.id:
        raise HTTPException(status_code=403, detail="Sem permissão para excluir este anexo")

    file_path = os.path.abspath(
        os.path.join(UPLOAD_DIR, str(ticket_id), attachment.stored_name)
    )
    if os.path.isfile(file_path):
        os.remove(file_path)

    db.delete(attachment)
    db.commit()
    return {"message": "Anexo excluído com sucesso"}
