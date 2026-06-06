from models import Ticket as TicketModel, User as UserModel
from models import StatusEnum, ProgressEnum, PriorityEnum
from datetime import datetime, UTC, timedelta

from sqlalchemy.sql import func


def dashboard_overview_service(
    current_user,
    db
):
    today = datetime.now(UTC).date()
    cutoff = datetime.now(UTC) - timedelta(hours=48)
    
    open_tickets = (
        db.query(TicketModel)
        .filter(TicketModel.status == StatusEnum.open)
        .count()
    )

    in_progress_tickets = (
        db.query(TicketModel)
        .filter(
            TicketModel.progress == ProgressEnum.in_progress,
            TicketModel.status == StatusEnum.open
        )
        .count()
    )

    feedback_tickets = (
        db.query(TicketModel)
        .filter(
            TicketModel.progress == ProgressEnum.feedback,
            TicketModel.status == StatusEnum.open
        )
        .count()
    )

    awaiting_confirmation_tickets = (
        db.query(TicketModel)
        .filter(
            TicketModel.progress == ProgressEnum.awaiting_confirmation,
            TicketModel.status == StatusEnum.open
        )
        .count()
    )

    unassigned_tickets = (
        db.query(TicketModel)
        .filter(
            TicketModel.assigned_to.is_(None),
            TicketModel.status == StatusEnum.open
        )
        .count()
    )

    high_priority_tickets = (
        db.query(TicketModel)
        .filter(
            TicketModel.priority == PriorityEnum.high,
            TicketModel.status == StatusEnum.open
        )
        .count()
    )

    created_today_tickets = (
        db.query(TicketModel)
        .filter(
            func.date(TicketModel.created_at) == today
        )
        .count()
    )

    stale_48h_tickets = (
        db.query(TicketModel)
        .filter(
            TicketModel.status == StatusEnum.open,
            TicketModel.updated_at < cutoff
        )
        .count()
    )

    return {
        "open_tickets": open_tickets,
        "in_progress_tickets": in_progress_tickets,
        "feedback_tickets": feedback_tickets,
        "awaiting_confirmation_tickets": awaiting_confirmation_tickets,

        "unassigned_tickets": unassigned_tickets,
        "stale_48h_tickets": stale_48h_tickets,
        "high_priority_tickets": high_priority_tickets,
        "created_today_tickets": created_today_tickets
    }