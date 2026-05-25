from fastapi import HTTPException
from sqlalchemy.orm import Session

from models import Hotel as HotelModel
from models import Team as TeamModel

def ensure_hotels_exist(hotel_ids: list[int], db: Session) -> None:
    if not hotel_ids:
        return
    
    unique_ids = set(hotel_ids)
    
    existing_ids = {
        h[0] for h in db.query(HotelModel.id)
        .filter(HotelModel.id.in_(unique_ids))
        .all()
    }
    
    missing_ids = unique_ids - existing_ids
    
    if missing_ids:
        raise HTTPException(status_code=400, detail=f"Hotéis inexistentes: {list(missing_ids)}")

def ensure_teams_exist(team_ids: list[int], db: Session) -> None:
    if not team_ids:
        return
    
    unique_ids = set(team_ids)

    existing_ids = {
        t[0] for t in db.query(TeamModel.id)
        .filter(TeamModel.id.in_(unique_ids))
        .all()
    }

    missing_ids = unique_ids - existing_ids

    if missing_ids:
        raise HTTPException(status_code=404, detail=f"Times inexistentes: {list(missing_ids)}")