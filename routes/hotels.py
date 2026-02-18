from fastapi import HTTPException
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from database import get_db

from models import RoleEnum


from models import Hotel as HotelModel
from models import User as UserModel

from schemas import HotelCreate, Hotel, HotelUpdate, HotelOut

from auth_utils import ensure_admin, get_current_user

router = APIRouter(prefix="/hotels", tags=["hotels"])

@router.get("/{hotel_id}", response_model=HotelOut)
def get_hotel(
    hotel_id: int,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user)
):
    
    hotel = db.query(HotelModel).filter(HotelModel.id == hotel_id).first()
    
    if not hotel:
        raise HTTPException(status_code=404, detail="Hotel not found")
    
    if current_user.role == RoleEnum.admin:
        return hotel
    
    user_hotel_ids = {uh.hotel_id for uh in current_user.hotels}
    
    if hotel_id not in user_hotel_ids:
        raise HTTPException(status_code=403, detail="Access to this hotel is denied")
    

@router.post("/", response_model=Hotel)
def create_hotel(
    hotel: HotelCreate, 
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(ensure_admin)
):
    
    existing_hotel_code = db.query(HotelModel).filter(HotelModel.code == hotel.code).first()
    
    if existing_hotel_code:
        raise HTTPException(status_code=400, detail="There is already an hotel registered for this code")
    
    existing_hotel_name = db.query(HotelModel).filter(HotelModel.name == hotel.name).first()
    
    if existing_hotel_name:
        raise HTTPException(status_code=400, detail="There is already an hotel registered with the same name")
    
    
    db_hotel = HotelModel(
        code=hotel.code, 
        name=hotel.name
    )
    
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

@router.delete("/{hotel_id}")
def delete_hotel(
    hotel_id: int, 
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(ensure_admin)
):
    hotel = db.query(HotelModel).filter(HotelModel.id == hotel_id).first()
    
    if not hotel:
        raise HTTPException(status_code=404, detail="Hotel not found")
    
    db.delete(hotel)
    db.commit()
    
    return { "message": f"Hotel: {hotel.name} - {hotel.code} - Deletado com sucesso." }
