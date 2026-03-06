from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from models import Ticket as TicketModel, Team as TeamModel, TicketLog as TicketLogModel
from models import User as UserModel, Category as CategoryModel
from models import LogActionEnum
from schemas import TicketCreate, TicketUpdate as TicketSchema, TicketOut, TicketUpdate, TicketWithComments, SubcategoryUpdate
from schemas import StatusEnum, ProgressEnum

from models import RoleEnum

from services.permissions import can_update_ticket_field
from services.authorization import ensure_can_assign_agent, ensure_user_can_access_ticket
from services.ticket_service import assign_agent_to_ticket, ensure_agent_belongs_to_ticket_assigned_team
from services.ticket_service import start_ticket_service, create_ticket_service, list_tickets_service, ticket_edit_service, assign_ticket_team_service, cancel_ticket_service, close_ticket_service, update_ticket_subcategory_service

from database import get_db 
from auth_utils import get_current_user

router = APIRouter(
    prefix="/tickets",
    tags=["tickets"]
)

@router.post("/", response_model=TicketSchema)
def create_ticket(
    ticket: TicketCreate, 
    db: Session = Depends(get_db), 
    current_user: UserModel = Depends(get_current_user)
):
    db_ticket = create_ticket_service(ticket, current_user, db)     
    db.commit()
    db.refresh(db_ticket)
    
    return db_ticket

@router.get("/", response_model=List[TicketOut])
def list_tickets(db: Session = Depends(get_db), current_user: UserModel = Depends(get_current_user)):

   return list_tickets_service(current_user, db)

@router.get("/{ticket_id}", response_model=TicketWithComments)
def get_ticket(ticket_id: int, db: Session = Depends(get_db), current_user: UserModel = Depends(get_current_user)):
    ticket = db.query(TicketModel).filter(TicketModel.id == ticket_id).first()
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    
    ensure_user_can_access_ticket(ticket, current_user)
    
    return ticket

@router.put("/{ticket_id}", response_model=TicketOut)
def update_ticket(
    ticket_id: int, 
    ticket_update: TicketUpdate,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user)
):
    ticket = ticket_edit_service(ticket_id, ticket_update, current_user, db)
    
    db.commit()
    db.refresh(ticket)
    
    return ticket

@router.put("/{ticket_id}/assign-team/{team_id}", response_model=TicketOut)
def assign_ticket_team(ticket_id: int, team_id: int, db: Session = Depends(get_db), current_user: UserModel = Depends(get_current_user)):
    
    ticket = assign_ticket_team_service(ticket_id, team_id, current_user, db)

    db.commit()
    db.refresh(ticket)
    
    return ticket

@router.put("/{ticket_id}/subcategory", response_model=TicketOut)
def update_ticket_subcategory(
    ticket_id: int,
    payload: SubcategoryUpdate,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user)
):

    ticket = update_ticket_subcategory_service(
        ticket_id,
        payload.subcategory_id,
        current_user,
        db
    )

    db.commit()
    db.refresh(ticket)

    return ticket

@router.put("/start-ticket/{ticket_id}", response_model=TicketOut)
def start_ticket(
    ticket_id: int,
    db: Session = Depends(get_db), 
    current_user: UserModel = Depends(get_current_user),
):
    
    ticket = start_ticket_service(ticket_id, current_user, db)
    
    db.commit()
    db.refresh(ticket)
    
    return ticket   

@router.put("/close-ticket/{ticket_id}", response_model=TicketOut)
def close_ticket(
    ticket_id: int, 
    db: Session = Depends(get_db), 
    current_user: UserModel = Depends(get_current_user)
):
    ticket = close_ticket_service(ticket_id, current_user, db)
    return ticket    

@router.put("/reopen-ticket/{ticket_id}", response_model=TicketOut)
def reopen_ticket(ticket_id: int, db: Session = Depends(get_db), current_user: UserModel = Depends(get_current_user)):
    
    ticket = db.query(TicketModel).filter(TicketModel.id == ticket_id).first()
    
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket não localizado")
    
    ensure_user_can_access_ticket(ticket, current_user)
    
    ticket.status = StatusEnum.open.value
    ticket.progress = ProgressEnum.in_progress.value
    
    db.add(ticket)
    
    log = TicketLogModel(
        user_id=current_user.id,
        ticket_id=ticket.id,
        action=LogActionEnum.ticket_reopened.value,
        value=LogActionEnum.ticket_reopened.value
    )
    
    db.add(log)
    
    db.commit()
    
    db.refresh(ticket)
    
    return ticket

@router.delete("/delete-ticket/{ticket_id}")
def delete_ticket(ticket_id: int, db: Session = Depends(get_db), current_user: UserModel = Depends(get_current_user)):
    ticket = db.query(TicketModel).filter(TicketModel.id == ticket_id).first()
    
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket não localizado")
    
    ensure_user_can_access_ticket(ticket_id, current_user)
    
    db.delete(ticket)  
    
    db.commit()
    
    return { "message": f"Ticket: {ticket_id} - Deletado com sucesso." }

@router.put("/{ticket_id}/assign-agent/{user_id}", response_model=TicketOut)
def assign_agent(
    ticket_id: int, 
    user_id: int, 
    db: Session = Depends(get_db), 
    current_user: UserModel = Depends(get_current_user)):

    ticket = db.query(TicketModel).filter(TicketModel.id == ticket_id).first()
    
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket não localizado")
    
    ensure_user_can_access_ticket(ticket, current_user)
    
    target_user = db.query(UserModel).filter(UserModel.id == user_id).first()
    
    if not target_user:
        raise HTTPException(status_code=404, detail="Usuário não localizado")
    
    ensure_can_assign_agent(ticket, current_user, target_user, db)
    
    ensure_agent_belongs_to_ticket_assigned_team(ticket, target_user)
    
    if ticket.assigned_to == target_user.id:
        return ticket
    
    assign_agent_to_ticket(ticket, current_user, target_user, db)
    
    db.commit()
    db.refresh(ticket)
    
    return ticket

@router.put("/{ticket_id}/cancel", response_model=TicketOut)
def cancel_ticket(
    ticket_id: int,
    current_user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    ticket = cancel_ticket_service(ticket_id, current_user, db)
    
    return ticket
