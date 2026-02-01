from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session

from auth_utils import get_current_user, get_db

from datetime import datetime

from models import TicketTimeLog
from models import User as UserModel, Ticket as TicketModel