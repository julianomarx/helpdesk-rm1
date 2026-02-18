from fastapi import HTTPException
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from database import get_db

from models import Hotel as HotelModel
from models import User as UserModel

from schemas import HotelCreate, Hotel, HotelUpdate, HotelOut

from auth_utils import ensure_admin

router = APIRouter(prefix="/hotels", tags=["hotels"])

@router.post("/", response_model=Hotel)
def create_hotel(hotel: HotelCreate, db: Session = Depends(get_db)):
    db_hotel = HotelModel(code=hotel.code, name=hotel.name)
    db.add(db_hotel)
    db.commit()
    db.refresh(db_hotel)
    return db_hotel

@router.put("/{hotel_id}", response_model=HotelOut)
def update_hotel(
    hotel_id: int,
    hotel_update: HotelUpdate,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(ensure_admin)
):
    hotel = db.query(HotelModel).filter(HotelModel.id == hotel_id).first()
    
    if not hotel:
        raise HTTPException(status_code=404, detail="Hotel not found")
    
    data = hotel_update.model_dump(exclude_unset=True)
    
    for field, new_value in data.items():
        
        old_value = getattr(hotel, field)
        
        if old_value == new_value:
            continue
        
        setattr(hotel, field, new_value)
    
    db.commit()
    db.refresh(hotel)
    
    return hotel