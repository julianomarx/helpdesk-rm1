from fastapi import HTTPException
from sqlalchemy.orm import Session
from models import User as UserModel, Team as TeamModel, UserTeam as UserTeamModel
from models import RoleEnum

def add_user_to_team_service(
    db: Session,
    user: UserModel,
    team: TeamModel
):
    already_member = any(
        ut.team_id == team.id for ut in user.teams
    )
    
    if already_member:
        return
    
    link = UserTeamModel(
        user_id=user.id,
        team_id=team.id
    )
    
    db.add(link)
    
def list_team_users_service(
    team_id: int,
    current_user: UserModel,
    db: Session
): 
    team = db.query(TeamModel).filter(TeamModel.id == team_id).first()
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")
    
    if current_user.role not in [RoleEnum.admin, RoleEnum.agent]:
        raise HTTPException(status_code=403, detail="Only admins and agents can list the users of a Team")
    
    team_users = (
        db.query(UserModel)
        .join(UserTeamModel, UserTeamModel.user_id == UserModel.id)
        .filter(UserTeamModel.team_id == team.id)
        .all()
    )
    
    return team_users