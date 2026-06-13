from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from auth_utils import get_current_user
from database import get_db
from models import Todo as TodoModel, User as UserModel, RoleEnum
from schemas import TodoCreate, TodoOut
from services.notification_service import create_notification, extract_mentioned_users

router = APIRouter(prefix="/todos", tags=["todos"])

ALLOWED_ROLES = {RoleEnum.admin, RoleEnum.agent}


def _require_staff(current_user: UserModel):
    if current_user.role not in ALLOWED_ROLES:
        raise HTTPException(status_code=403, detail="Acesso negado")


@router.get("", response_model=list[TodoOut])
def list_todos(
    current_user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _require_staff(current_user)
    return (
        db.query(TodoModel)
        .filter(
            (TodoModel.assignee_id == current_user.id)
            | (TodoModel.creator_id == current_user.id)
        )
        .order_by(TodoModel.done.asc(), TodoModel.created_at.desc())
        .all()
    )


@router.get("/pending-count")
def pending_count(
    current_user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _require_staff(current_user)
    count = (
        db.query(TodoModel)
        .filter(TodoModel.assignee_id == current_user.id, TodoModel.done == False)
        .count()
    )
    return {"count": count}


@router.post("", response_model=TodoOut, status_code=201)
def create_todo(
    payload: TodoCreate,
    current_user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _require_staff(current_user)
    mentioned = extract_mentioned_users(payload.body, db, exclude_user_id=current_user.id)
    if not mentioned:
        raise HTTPException(status_code=422, detail="Mencione um usuário com @nome para atribuir o TODO")

    assignee = mentioned[0]
    todo = TodoModel(
        creator_id=current_user.id,
        assignee_id=assignee.id,
        body=payload.body,
    )
    db.add(todo)
    db.flush()

    first_name = current_user.name.split()[0] if current_user.name else current_user.name
    create_notification(
        db, assignee.id, "todo_assigned",
        f"@{first_name} atribuiu um TODO para você",
        payload.body,
    )
    db.commit()
    db.refresh(todo)
    return todo


@router.put("/{todo_id}/done")
def mark_done(
    todo_id: int,
    current_user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _require_staff(current_user)
    todo = db.query(TodoModel).filter(TodoModel.id == todo_id).first()
    if not todo:
        raise HTTPException(status_code=404, detail="TODO não encontrado")
    if todo.assignee_id != current_user.id:
        raise HTTPException(status_code=403, detail="Apenas o responsável pode concluir o TODO")
    if todo.done:
        return {"ok": True}

    todo.done = True
    todo.done_at = datetime.now(timezone.utc)
    db.flush()

    if todo.creator_id != current_user.id:
        first_name = current_user.name.split()[0] if current_user.name else current_user.name
        create_notification(
            db, todo.creator_id, "todo_done",
            f"@{first_name} concluiu o TODO",
            todo.body,
        )
    db.commit()
    return {"ok": True}


@router.delete("/{todo_id}")
def delete_todo(
    todo_id: int,
    current_user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _require_staff(current_user)
    todo = db.query(TodoModel).filter(TodoModel.id == todo_id).first()
    if not todo:
        raise HTTPException(status_code=404, detail="TODO não encontrado")
    if todo.creator_id != current_user.id and current_user.role != RoleEnum.admin:
        raise HTTPException(status_code=403, detail="Sem permissão")
    db.delete(todo)
    db.commit()
    return {"ok": True}
