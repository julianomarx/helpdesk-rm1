from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from auth_utils import get_current_user
from models import Notification as NotificationModel, User as UserModel

router = APIRouter(prefix="/notifications", tags=["notifications"])


def _serialize(n: NotificationModel):
    return {
        "id": n.id,
        "type": n.type,
        "title": n.title,
        "body": n.body,
        "ticket_id": n.ticket_id,
        "mural_post_id": n.mural_post_id,
        "read": n.read,
        "created_at": n.created_at.isoformat() if n.created_at else None,
    }


@router.get("")
def get_notifications(
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
):
    notifs = (
        db.query(NotificationModel)
        .filter(NotificationModel.user_id == current_user.id)
        .order_by(NotificationModel.created_at.desc())
        .limit(40)
        .all()
    )
    return [_serialize(n) for n in notifs]


@router.get("/unread-count")
def get_unread_count(
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
):
    count = (
        db.query(NotificationModel)
        .filter(NotificationModel.user_id == current_user.id, NotificationModel.read == False)
        .count()
    )
    return {"count": count}


@router.put("/read-all")
def mark_all_read(
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
):
    db.query(NotificationModel).filter(
        NotificationModel.user_id == current_user.id,
        NotificationModel.read == False,
    ).update({"read": True})
    db.commit()
    return {"ok": True}


@router.put("/{notif_id}/read")
def mark_read(
    notif_id: int,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
):
    notif = db.query(NotificationModel).filter(
        NotificationModel.id == notif_id,
        NotificationModel.user_id == current_user.id,
    ).first()
    if not notif:
        raise HTTPException(status_code=404, detail="Notificação não encontrada")
    notif.read = True
    db.commit()
    return {"ok": True}


@router.delete("/{notif_id}")
def delete_notification(
    notif_id: int,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
):
    notif = db.query(NotificationModel).filter(
        NotificationModel.id == notif_id,
        NotificationModel.user_id == current_user.id,
    ).first()
    if not notif:
        raise HTTPException(status_code=404, detail="Notificação não encontrada")
    db.delete(notif)
    db.commit()
    return {"ok": True}
