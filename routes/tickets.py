from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from models import Ticket as TicketModel
from schemas import TicketCreate, Ticket as TicketSchema
from database import get_db

router = APIRouter(
    prefix="/tickets",
    tags=["tickets"]
)

@router.post("/", response_model=TicketSchema)
def create_ticket(ticket: TicketCreate, db: Session = Depends(get_db)):
    db_ticket = TicketModel(
        title=ticket.title,
        description=ticket.description,
        status=ticket.status,
        priority=ticket.priority,
        created_by=ticket.created_by,
        assigned_to=ticket.assigned_to
    )
    db.add(db_ticket)
    db.commit()
    db.refresh(db_ticket)
    return db_ticket

@router.get("/", response_model=List[TicketSchema])
def list_tickets(db: Session = Depends(get_db)):
    tickets = db.query(TicketModel).all()
    return tickets

@router.get("/{ticket_id}", response_model=TicketSchema)
def get_ticket(ticket_id: int, db: Session = Depends(get_db)):
    ticket = db.query(TicketModel).filter(TicketModel.id == ticket_id).first()
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    return ticket
