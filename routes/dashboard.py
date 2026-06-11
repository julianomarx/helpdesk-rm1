from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

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