from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from models import Ticket as TicketModel
from models import User as UserModel
from schemas import TicketCreate, Ticket, TicketUpdate as TicketSchema, TicketOut, TicketUpdate
from database import get_db
from auth_utils import get_current_user

router = APIRouter(
    prefix="/tickets",
    tags=["tickets"]
)

@router.post("/", response_model=TicketSchema)
def create_ticket(ticket: TicketCreate, db: Session = Depends(get_db), current_user: UserModel = Depends(get_current_user)):
    db_ticket = TicketModel(
        title=ticket.title,
        description=ticket.description,
        status=ticket.status,
        priority=ticket.priority,
        created_by=ticket.created_by,
        assigned_to=ticket.assigned_to,
        hotel_id=ticket.hotel_id
    )
    db.add(db_ticket)
    db.commit()
    db.refresh(db_ticket)
    return db_ticket

@router.get("/", response_model=List[TicketOut])
def list_tickets(db: Session = Depends(get_db), current_user: UserModel = Depends(get_current_user)):
    tickets = db.query(TicketModel).all()
    return tickets

@router.get("/{ticket_id}", response_model=TicketSchema)
def get_ticket(ticket_id: int, db: Session = Depends(get_db), current_user: UserModel = Depends(get_current_user)):
    ticket = db.query(TicketModel).filter(TicketModel.id == ticket_id).first()
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    return ticket

@router.put("/{ticket_id}", response_model=TicketOut)
def update_ticket(ticket_id: int, ticket_update: TicketUpdate, db: Session = Depends(get_db), current_user: UserModel = Depends(get_current_user)):
    ticket = db.query(TicketModel).filter((TicketModel.id == ticket_id)).first()
    if not ticket:
        raise HTTPException(status_code=404, detail="Chamado não localizado")
    
    data = ticket_update.model_dump(exclude_unset=True) 

    #falta fazer validações de segurança -> fiz este serviço de preguiçoso mas depois eu arrumo

    if "title" in data and data["title"] == ticket.title:
        data.pop("title")

    if "description" in data and data["description"] == ticket.description:
        data.pop("description")

    if "priority" in data and data["priority"] == ticket.priority:
        data.pop("priority")

    if "status" in data and data["status"] == ticket.status:    
        data.pop("status")  

    if "progress" in data and data["progress"] == ticket.progress:
        data.pop("progress")
    
    if "assigned_to" in data and data["assigned_to"] == ticket.assigned_to:
        data.pop("assigned_to")

    for field, value in data.items():
        setattr(ticket, field, value)

    db.commit()
    db.refresh(ticket)
    return ticket