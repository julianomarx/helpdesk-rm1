from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import List

from models import User as UserModel
from schemas import (
    DashboardOverview, DashboardOperational, DashboardProductivity,
    DashboardBottlenecks, DashboardVolume, DashboardHistory, DashboardSLA,
)
from database import get_db
from auth_utils import get_current_user
from services.dashboard_service import (
    dashboard_overview_service,
    operational_dashboard_service,
    productivity_dashboard_service,
    bottlenecks_dashboard_service,
    volume_dashboard_service,
    history_dashboard_service,
    sla_dashboard_service,
)

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/overview", response_model=DashboardOverview)
def get_dashboard_overview(
    current_user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    return dashboard_overview_service(current_user, db)


@router.get("/operational", response_model=DashboardOperational)
def get_operational(
    current_user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    return operational_dashboard_service(current_user, db)


@router.get("/productivity", response_model=DashboardProductivity)
def get_productivity(
    current_user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    return productivity_dashboard_service(current_user, db)


@router.get("/bottlenecks", response_model=DashboardBottlenecks)
def get_bottlenecks(
    current_user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    return bottlenecks_dashboard_service(current_user, db)


@router.get("/volume", response_model=DashboardVolume)
def get_volume(
    current_user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    return volume_dashboard_service(current_user, db)


@router.get("/history", response_model=DashboardHistory)
def get_history(
    current_user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    return history_dashboard_service(current_user, db)


@router.get("/sla", response_model=DashboardSLA)
def get_sla_dashboard(
    current_user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    return sla_dashboard_service(current_user, db)


@router.get("/bottlenecks/hotels")
def get_bottlenecks_hotels_paginated(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    current_user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    offset = (page - 1) * page_size
    rows = db.execute(text("""
        SELECT h.name, ROUND(AVG(TIMESTAMPDIFF(HOUR, tk.created_at, tk.updated_at)), 1) AS avg_hours,
               COUNT(tk.id) AS ticket_count
        FROM tickets tk
        JOIN hotels h ON tk.hotel_id = h.id
        WHERE tk.status = 'closed'
        GROUP BY h.id, h.name
        ORDER BY avg_hours DESC
        LIMIT :limit OFFSET :offset
    """), {"limit": page_size, "offset": offset}).fetchall()

    total = db.execute(text("""
        SELECT COUNT(DISTINCT tk.hotel_id) FROM tickets tk
        WHERE tk.status = 'closed' AND tk.hotel_id IS NOT NULL
    """)).scalar() or 0

    return {
        "items": [{"name": r.name, "avg_hours": float(r.avg_hours or 0), "ticket_count": r.ticket_count} for r in rows],
        "total": total,
        "page": page,
        "page_size": page_size,
        "pages": max(1, -(-total // page_size))
    }