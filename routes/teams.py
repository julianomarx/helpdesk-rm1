from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from models import Team as TeamModel
from schemas import TeamBase, Team
from database import get_db
from auth_utils import get_current_user

router = APIRouter(
    prefix="/teams",
    tags=["teams"]
)

@router.post("/", response_model=Team)
def create_team(team: TeamBase, db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    db_team = TeamModel(name=team.name)
    db.add(db_team)
    db.commit()
    db.refresh(db_team)
    return db_team


@router.get("/", response_model=List[Team])
def list_teams(db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    return db.query(TeamModel).all()
