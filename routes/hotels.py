from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from database import get_db
from models import Hotel as HotelModel
from schemas import HotelCreate, Hotel

router = APIRouter(prefix="/hotels", tags=["hotels"])

@router.post("/", response_model=Hotel)
def create_hotel(hotel: HotelCreate, db: Session = Depends(get_db)):
    db_hotel = HotelModel(code=hotel.code, name=hotel.name)
    db.add(db_hotel)
    db.commit()
    db.refresh(db_hotel)
    return db_hotel
