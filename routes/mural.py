from datetime import datetime, timezone, timedelta
from math import ceil

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, joinedload
from sqlalchemy.exc import IntegrityError

from auth_utils import get_current_user
from database import get_db
from models import (
    MuralPost as MuralPostModel,
    MuralComment as MuralCommentModel,
    MuralAck as MuralAckModel,
    User as UserModel,
    RoleEnum,
)
from schemas import MuralPostCreate, MuralPostOut, MuralCommentCreate, MuralCommentOut, MuralListOut
from services.notification_service import (
    create_notification,
    notify_all_staff,
    extract_mentioned_users,
)

router = APIRouter(prefix="/mural", tags=["mural"])

STAFF_ROLES = {RoleEnum.admin, RoleEnum.agent}


def _require_staff(user: UserModel):
    if user.role not in STAFF_ROLES:
        raise HTTPException(status_code=403, detail="Acesso negado")


def _build_post_out(post: MuralPostModel, current_user_id: int) -> MuralPostOut:
    ack_count = len(post.acks)
    acked_by_me = any(a.user_id == current_user_id for a in post.acks)
    return MuralPostOut(
        id=post.id,
        body=post.body,
        created_at=post.created_at,
        author=post.author,
        comments=[
            MuralCommentOut(
                id=c.id,
                body=c.body,
                created_at=c.created_at,
                author=c.author,
            )
            for c in post.comments
        ],
        ack_count=ack_count,
        acked_by_me=acked_by_me,
    )


@router.get("", response_model=MuralListOut)
def list_posts(
    start_date: datetime = None,
    end_date: datetime = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=50),
    current_user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _require_staff(current_user)

    if start_date is None:
        start_date = datetime.now(timezone.utc) - timedelta(days=7)
    if end_date is None:
        end_date = datetime.now(timezone.utc)

    q = (
        db.query(MuralPostModel)
        .options(
            joinedload(MuralPostModel.author),
            joinedload(MuralPostModel.comments).joinedload(MuralCommentModel.author),
            joinedload(MuralPostModel.acks),
        )
        .filter(
            MuralPostModel.created_at >= start_date,
            MuralPostModel.created_at <= end_date,
        )
        .order_by(MuralPostModel.created_at.desc())
    )

    total = q.count()
    posts = q.offset((page - 1) * page_size).limit(page_size).all()

    return MuralListOut(
        items=[_build_post_out(p, current_user.id) for p in posts],
        total=total,
        page=page,
        page_size=page_size,
        pages=ceil(total / page_size) if total else 1,
    )


@router.post("", response_model=MuralPostOut, status_code=201)
def create_post(
    payload: MuralPostCreate,
    current_user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _require_staff(current_user)

    post = MuralPostModel(author_id=current_user.id, body=payload.body)
    db.add(post)
    db.flush()

    first_name = current_user.name.split()[0] if current_user.name else current_user.name
    has_all = "@all" in payload.body.lower() or "@todos" in payload.body.lower()

    if has_all:
        notify_all_staff(
            db,
            exclude_user_id=current_user.id,
            type="mural_mention",
            title=f"@{first_name} publicou no Mural para todos",
            body=payload.body,
            mural_post_id=post.id,
        )
    else:
        mentioned = extract_mentioned_users(payload.body, db, exclude_user_id=current_user.id)
        for u in mentioned:
            create_notification(
                db, u.id, "mural_mention",
                f"@{first_name} mencionou você no Mural",
                payload.body,
                mural_post_id=post.id,
            )

    db.commit()
    db.refresh(post)
    return _build_post_out(post, current_user.id)


@router.post("/{post_id}/comments", response_model=MuralCommentOut, status_code=201)
def add_comment(
    post_id: int,
    payload: MuralCommentCreate,
    current_user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _require_staff(current_user)

    post = db.query(MuralPostModel).filter(MuralPostModel.id == post_id).first()
    if not post:
        raise HTTPException(status_code=404, detail="Post não encontrado")

    comment = MuralCommentModel(post_id=post_id, author_id=current_user.id, body=payload.body)
    db.add(comment)
    db.flush()

    first_name = current_user.name.split()[0] if current_user.name else current_user.name

    # Notify post author if different from commenter
    if post.author_id != current_user.id:
        create_notification(
            db, post.author_id, "mural_comment",
            f"@{first_name} comentou no seu post do Mural",
            payload.body,
            mural_post_id=post_id,
        )

    # Notify @mentions in comment (excluding commenter)
    mentioned = extract_mentioned_users(payload.body, db, exclude_user_id=current_user.id)
    for u in mentioned:
        if u.id != post.author_id:
            create_notification(
                db, u.id, "mural_mention",
                f"@{first_name} mencionou você em um comentário do Mural",
                payload.body,
                mural_post_id=post_id,
            )

    db.commit()
    db.refresh(comment)
    return MuralCommentOut(
        id=comment.id,
        body=comment.body,
        created_at=comment.created_at,
        author=comment.author,
    )


@router.post("/{post_id}/ack", status_code=200)
def ack_post(
    post_id: int,
    current_user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _require_staff(current_user)

    post = db.query(MuralPostModel).filter(MuralPostModel.id == post_id).first()
    if not post:
        raise HTTPException(status_code=404, detail="Post não encontrado")

    existing = (
        db.query(MuralAckModel)
        .filter(MuralAckModel.post_id == post_id, MuralAckModel.user_id == current_user.id)
        .first()
    )
    if existing:
        return {"acked": True, "ack_count": len(post.acks)}

    ack = MuralAckModel(post_id=post_id, user_id=current_user.id)
    db.add(ack)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()

    db.refresh(post)
    return {"acked": True, "ack_count": len(post.acks)}


@router.delete("/{post_id}", status_code=200)
def delete_post(
    post_id: int,
    current_user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _require_staff(current_user)

    post = db.query(MuralPostModel).filter(MuralPostModel.id == post_id).first()
    if not post:
        raise HTTPException(status_code=404, detail="Post não encontrado")
    if post.author_id != current_user.id and current_user.role != RoleEnum.admin:
        raise HTTPException(status_code=403, detail="Sem permissão")

    db.delete(post)
    db.commit()
    return {"ok": True}
