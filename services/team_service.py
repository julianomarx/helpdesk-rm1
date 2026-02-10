from sqlalchemy.orm import Session
from models import User as UserModel, Team as TeamModel, UserTeam as UserTeamModel

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