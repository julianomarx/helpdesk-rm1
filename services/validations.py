from fastapi import HTTPException
from sqlalchemy.orm import Session

from models import Hotel as HotelModel

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

    