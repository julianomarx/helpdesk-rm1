from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from models import Team as TeamModel
from models import User as UserModel, UserTeam as UserTeamModel
from schemas import TeamBase, Team
from database import get_db
from auth_utils import get_current_user

from services.authorization import ensure_can_manage_team_members

from services.team_service import add_user_to_team_service

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


@router.post("/{team_id}/add-user/{user_id}/")
def add_user_to_team(
    team_id: int,
    user_id: int,
    current_user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    
    team = db.query(TeamModel).filter(TeamModel.id == team_id).first()
    
    if not team:
        raise HTTPException(status_code=404, detail="Time não localiado")
    
    target_user = db.query(UserModel).filter(UserModel.id == user_id).first()
    
    if not target_user:
        raise HTTPException(status_code=404, detail="Usuário não localizado")
    
    ensure_can_manage_team_members(current_user, target_user, team)
    
    add_user_to_team_service(db, target_user, team)
    
    db.commit()
    
    return {"message": "User added to team successfully"}
