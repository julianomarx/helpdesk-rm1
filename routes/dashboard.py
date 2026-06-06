from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session


from models import TicketComment as CommentModel
from models import User as UserModel
from models import Ticket as TicketModel
from schemas import DashboardOverview

from database import get_db
from auth_utils import get_current_user

from services.dashboard_service import dashboard_overview_service

router = APIRouter(
    prefix="/dashboard",
    tags=["dashboard"]
)

@router.get("/overview", response_model=DashboardOverview)
def get_dashboard_overview(
    current_user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    return dashboard_overview_service(current_user, db)