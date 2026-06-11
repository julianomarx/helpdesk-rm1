from datetime import date, datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, joinedload

from database import get_db
from models import (
    User as UserModel,
    Ticket as TicketModel,
    TicketLog as TicketLogModel,
    TicketComment as TicketCommentModel,
    RoleEnum,
)
from services.authorization import ensure_admin

router = APIRouter(prefix="/reports", tags=["reports"])


@router.get("/agents")
def list_report_agents(
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(ensure_admin),
):
    agents = (
        db.query(UserModel)
        .filter(UserModel.role.in_([RoleEnum.admin, RoleEnum.agent]))
        .order_by(UserModel.name)
        .all()
    )
    return [{"id": a.id, "name": a.name, "email": a.email, "role": a.role} for a in agents]


@router.get("/activity")
def get_activity_report(
    user_id: int = Query(...),
    start_date: date = Query(...),
    end_date: date = Query(...),
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(ensure_admin),
):
    if start_date > end_date:
        raise HTTPException(status_code=400, detail="Data inicial não pode ser maior que a data final")

    agent = db.query(UserModel).filter(UserModel.id == user_id).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")

    start_dt = datetime(start_date.year, start_date.month, start_date.day, 0, 0, 0, tzinfo=timezone.utc)
    end_dt = datetime(end_date.year, end_date.month, end_date.day, 23, 59, 59, 999999, tzinfo=timezone.utc)

    total_actions = (
        db.query(TicketLogModel)
        .filter(
            TicketLogModel.user_id == user_id,
            TicketLogModel.created_at >= start_dt,
            TicketLogModel.created_at <= end_dt,
        )
        .count()
    )

    log_rows = (
        db.query(TicketLogModel.ticket_id)
        .filter(
            TicketLogModel.user_id == user_id,
            TicketLogModel.created_at >= start_dt,
            TicketLogModel.created_at <= end_dt,
        )
        .distinct()
        .all()
    )
    log_ticket_ids = [r.ticket_id for r in log_rows]

    tickets_closed_count = (
        db.query(TicketLogModel.ticket_id)
        .filter(
            TicketLogModel.user_id == user_id,
            TicketLogModel.action == "ticket_closed",
            TicketLogModel.created_at >= start_dt,
            TicketLogModel.created_at <= end_dt,
        )
        .distinct()
        .count()
    )

    tickets_opened_count = (
        db.query(TicketModel)
        .filter(
            TicketModel.created_by == user_id,
            TicketModel.created_at >= start_dt,
            TicketModel.created_at <= end_dt,
        )
        .count()
    )

    comments_count = (
        db.query(TicketCommentModel)
        .filter(
            TicketCommentModel.user_id == user_id,
            TicketCommentModel.created_at >= start_dt,
            TicketCommentModel.created_at <= end_dt,
        )
        .count()
    )

    ticket_list = []
    by_priority = {"low": 0, "medium": 0, "high": 0}
    by_status = {"open": 0, "closed": 0, "cancelled": 0}

    if log_ticket_ids:
        tickets = (
            db.query(TicketModel)
            .options(joinedload(TicketModel.hotel), joinedload(TicketModel.category))
            .filter(TicketModel.id.in_(log_ticket_ids))
            .order_by(TicketModel.updated_at.desc())
            .all()
        )
        for t in tickets:
            prio = t.priority.value if hasattr(t.priority, "value") else str(t.priority)
            stat = t.status.value if hasattr(t.status, "value") else str(t.status)
            prog = t.progress.value if hasattr(t.progress, "value") else str(t.progress)
            by_priority[prio] = by_priority.get(prio, 0) + 1
            by_status[stat] = by_status.get(stat, 0) + 1
            ticket_list.append({
                "id": t.id,
                "title": t.title,
                "status": stat,
                "priority": prio,
                "progress": prog,
                "hotel": t.hotel.name if t.hotel else "—",
                "category": t.category.name if t.category else "—",
            })

    return {
        "agent": {"id": agent.id, "name": agent.name, "email": agent.email, "role": agent.role},
        "period": {"start": start_date.isoformat(), "end": end_date.isoformat()},
        "summary": {
            "tickets_interacted": len(log_ticket_ids),
            "tickets_closed": tickets_closed_count,
            "tickets_opened": tickets_opened_count,
            "comments_made": comments_count,
            "total_actions": total_actions,
        },
        "by_priority": by_priority,
        "by_status": by_status,
        "ticket_list": ticket_list,
    }
