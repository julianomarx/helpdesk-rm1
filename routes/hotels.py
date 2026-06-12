from fastapi import HTTPException
from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from database import get_db

from models import RoleEnum, StatusEnum, ProgressEnum
from models import Hotel as HotelModel
from models import User as UserModel
from models import Ticket as TicketModel

from schemas import HotelCreate, Hotel, HotelUpdate, HotelOut

from auth_utils import get_current_user
from services.authorization import ensure_admin

router = APIRouter(prefix="/hotels", tags=["hotels"])

@router.get("/", response_model=list[Hotel])
def list_hotels(
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(ensure_admin)
):
    return db.query(HotelModel).order_by(HotelModel.name).all()

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

@router.get("/{hotel_id}/stats")
def get_hotel_stats(
    hotel_id: int,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(ensure_admin)
):
    hotel = db.query(HotelModel).filter(HotelModel.id == hotel_id).first()
    if not hotel:
        raise HTTPException(status_code=404, detail="Hotel not found")

    by_status = db.query(TicketModel.status, func.count(TicketModel.id)).filter(
        TicketModel.hotel_id == hotel_id
    ).group_by(TicketModel.status).all()

    by_progress = db.query(TicketModel.progress, func.count(TicketModel.id)).filter(
        TicketModel.hotel_id == hotel_id,
        TicketModel.status == StatusEnum.open
    ).group_by(TicketModel.progress).all()

    recent = db.query(TicketModel).filter(
        TicketModel.hotel_id == hotel_id
    ).order_by(TicketModel.created_at.desc()).limit(10).all()

    status_map = {s.value: c for s, c in by_status}
    progress_map = {p.value: c for p, c in by_progress}

    return {
        "total": sum(status_map.values()),
        "open": status_map.get("open", 0),
        "closed": status_map.get("closed", 0),
        "cancelled": status_map.get("cancelled", 0),
        "by_progress": progress_map,
        "recent": [
            {
                "id": t.id,
                "title": t.title,
                "status": t.status.value,
                "progress": t.progress.value,
                "priority": t.priority.value,
                "created_at": t.created_at.isoformat() if t.created_at else None,
            }
            for t in recent
        ],
    }


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
