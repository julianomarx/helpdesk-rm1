import os
import uuid

from fastapi import UploadFile, HTTPException
from sqlalchemy.orm import Session
from models import User as UserModel, Ticket as TicketModel, Attachment as AttachmentModel
from services.authorization import ensure_user_can_access_ticket
from config import TICKETS_DIR as UPLOAD_DIR

MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB

ALLOWED_MIME_TYPES = {
    "image/jpeg", "image/jpg", "image/png", "image/gif", "image/webp",
    "application/pdf",
    "application/msword",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/vnd.ms-excel",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "text/plain", "text/csv",
    "application/zip", "application/x-zip-compressed",
}

ALLOWED_EXTENSIONS = {
    ".jpg", ".jpeg", ".png", ".gif", ".webp",
    ".pdf", ".doc", ".docx", ".xls", ".xlsx",
    ".txt", ".csv", ".zip",
}

EXTENSION_TO_MIME = {
    ".jpg":  {"image/jpeg", "image/jpg"},
    ".jpeg": {"image/jpeg", "image/jpg"},
    ".png":  {"image/png"},
    ".gif":  {"image/gif"},
    ".webp": {"image/webp"},
    ".pdf":  {"application/pdf"},
    ".doc":  {"application/msword"},
    ".docx": {"application/vnd.openxmlformats-officedocument.wordprocessingml.document"},
    ".xls":  {"application/vnd.ms-excel"},
    ".xlsx": {"application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"},
    ".txt":  {"text/plain"},
    ".csv":  {"text/csv", "text/plain", "application/csv"},
    ".zip":  {"application/zip", "application/x-zip-compressed"},
}


def sanitize_filename(name: str) -> str:
    name = os.path.basename(name).strip()
    allowed = set(
        "abcdefghijklmnopqrstuvwxyz"
        "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
        "0123456789._-() "
    )
    name = "".join(c for c in name if c in allowed)
    name = name[:200].strip() or "arquivo"
    return name


async def save_attachment_service(
    ticket_id: int,
    file: UploadFile,
    current_user: UserModel,
    db: Session
):
    ticket = db.query(TicketModel).filter(TicketModel.id == ticket_id).first()
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket não encontrado")

    ensure_user_can_access_ticket(ticket, current_user, db)

    # — Lê o conteúdo para validar tamanho
    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=413,
            detail=f"Arquivo muito grande. Tamanho máximo permitido: {MAX_FILE_SIZE // 1024 // 1024} MB"
        )
    if len(content) == 0:
        raise HTTPException(status_code=400, detail="Arquivo vazio não é permitido")

    # — Valida extensão
    original_name = file.filename or "arquivo"
    ext = os.path.splitext(original_name)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Tipo de arquivo não permitido: '{ext}'. "
                   f"Permitidos: {', '.join(sorted(ALLOWED_EXTENSIONS))}"
        )

    # — Valida MIME type
    mime = (file.content_type or "").lower().split(";")[0].strip()
    if mime not in ALLOWED_MIME_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Tipo MIME não permitido: '{mime}'"
        )

    # — Verifica consistência extensão × MIME (evita renomear .exe para .pdf)
    expected_mimes = EXTENSION_TO_MIME.get(ext, set())
    if expected_mimes and mime not in expected_mimes:
        raise HTTPException(
            status_code=400,
            detail="Conteúdo do arquivo não corresponde à extensão informada"
        )

    # — Sanitiza nome original e gera nome único para armazenamento
    clean_name = sanitize_filename(original_name)
    stored_name = f"{uuid.uuid4()}{ext}"
    ticket_dir = f"{UPLOAD_DIR}/{ticket.id}"
    os.makedirs(ticket_dir, exist_ok=True)
    file_path = f"{ticket_dir}/{stored_name}"

    with open(file_path, "wb") as f:
        f.write(content)

    attachment = AttachmentModel(
        ticket_id=ticket_id,
        file_name=clean_name,
        stored_name=stored_name,
        mime_type=mime,
        file_size=len(content),
        uploaded_by=current_user.id
    )

    db.add(attachment)
    db.commit()
    db.refresh(attachment)
    return attachment
