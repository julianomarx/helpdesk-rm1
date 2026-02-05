from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from models import Ticket as TicketModel, Team as TeamModel, TicketLog as TicketLogModel
from models import User as UserModel, Category as CategoryModel
from schemas import TicketCreate, Ticket, TicketUpdate as TicketSchema, TicketOut, TicketUpdate, TicketWithComments
from schemas import StatusEnum, ProgressEnum

from models import LogActionEnum

from services.ticket_logs import FIELD_TO_ACTION

from database import get_db
from auth_utils import get_current_user, can_access_ticket

router = APIRouter(
    prefix="/tickets",
    tags=["tickets"]
)

def get_team_for_category(category_id: int, db: Session) -> int:
    category = db.query(CategoryModel).filter(CategoryModel.id == category_id).first()
    return category.team_id if category else None

@router.post("/", response_model=TicketSchema)
def create_ticket(ticket: TicketCreate, db: Session = Depends(get_db), current_user: UserModel = Depends(get_current_user)):
    
    assigned_team_id = get_team_for_category(ticket.category_id, db)
    
    db_ticket = TicketModel(
        title=ticket.title,
        description=ticket.description,
        status=StatusEnum.open.value,       
        progress=ProgressEnum.waiting.value, 
        priority=ticket.priority,
        created_by=current_user.id,
        hotel_id=ticket.hotel_id,
        category_id=ticket.category_id,
        subcategory_id=ticket.subcategory_id,
        assigned_team_id=assigned_team_id
    )
    
    db.add(db_ticket)
    
    db.flush()
    
    createdTicketLog = TicketLogModel(
        ticket_id=db_ticket.id,
        user_id=current_user.id,
        action=LogActionEnum.created.value,
        value=StatusEnum.open.value
    )
    
    teamAssignLog = TicketLogModel(
        ticket_id=db_ticket.id,
        user_id=current_user.id,
        action=LogActionEnum.team_changed.value,
        value=str(assigned_team_id)
    )
    
    db.add(createdTicketLog)
    db.add(teamAssignLog)
    
    db.commit()
    db.refresh(db_ticket)
    
    return db_ticket

@router.get("/", response_model=List[TicketOut])
def list_tickets(db: Session = Depends(get_db), current_user: UserModel = Depends(get_current_user)):
    
    query = db.query(TicketModel)
    
    if current_user.role not in ["admin", "agent"]:
        
        #Pega apenas os hoteis que o cabra tem acesso
        
        print(current_user.hotels)
        
        hotel_ids = [uh.hotel.id for uh in current_user.hotels]
        query = query.filter(TicketModel.hotel_id.in_(hotel_ids))
    
    tickets = query.all()
    return tickets

@router.get("/{ticket_id}", response_model=TicketWithComments)
def get_ticket(ticket_id: int, db: Session = Depends(get_db), current_user: UserModel = Depends(get_current_user)):
    ticket = db.query(TicketModel).filter(TicketModel.id == ticket_id).first()
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    
    return ticket

@router.put("/{ticket_id}", response_model=TicketOut)
def update_ticket(
    ticket_id: int, 
    ticket_update: TicketUpdate,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user)
):
    ticket = db.query(TicketModel).filter(TicketModel.id == ticket_id).first()
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket não localizado")
    
    if not can_access_ticket(ticket, current_user):
        raise HTTPException(status_code=403, detail="Acesso negado ao ticket")
    
    
    logs = []
    
    data = ticket_update.model_dump(exclude_unset=True)
    
    for field, new_value in data.items():
        
        old_value = getattr(ticket, field)
        
        if old_value == new_value:
            continue
        
        setattr(ticket, field, new_value)
        
        action = FIELD_TO_ACTION.get(field)
        if not action:
            continue
        
        logs.append(
            TicketLogModel(
                ticket_id=ticket.id,
                user_id=current_user.id,
                action=action.value,
                value=str(new_value)
            )
        )
        
    if logs:
        print(logs)
        db.add_all(logs)
    
    db.commit()
    db.refresh(ticket)
    
    return ticket

@router.put("/{ticket_id}/assign_team/{team_id}", response_model=TicketOut)
def assign_ticket_team(ticket_id: int, team_id: int, db: Session = Depends(get_db), current_user: UserModel = Depends(get_current_user)):
    
    ticket = db.query(TicketModel).filter(TicketModel.id == ticket_id).first()
    if not ticket:
        raise HTTPException(404, "Ticket não encontrado")
    
    team = db.query(TeamModel).filter(TeamModel.id == team_id).first()
    if not team:
        raise HTTPException(404, "Equipe não encontrada")
    
    ticket.assigned_team_id = team_id
    
    log = TicketLogModel(
        ticket_id=ticket.id,
        user_id=current_user.id,
        action=LogActionEnum.team_changed.value,
        value=team_id
    )
    
    db.add(log)
    db.commit()
    
    db.refresh(ticket)
    
    return ticket

@router.put("/close-ticket/{ticket_id}", response_model=TicketOut)
def close_ticket(ticket_id: int, db: Session = Depends(get_db), current_user: UserModel = Depends(get_current_user)):
    
    ticket = db.query(TicketModel).filter(TicketModel.id == ticket_id).first()
    
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket não localizado")
    
    #Checar permissão 
    if not can_access_ticket(ticket, current_user):
        raise HTTPException(status_code=403, detail="Acesso negado ao ticket" ) 
    
    ticket.status = StatusEnum.closed.value
    ticket.progress = ProgressEnum.done.value
    
    
    log = TicketLogModel(
        user_id=current_user.id,
        ticket_id=ticket.id,
        action=LogActionEnum.ticket_closed.value,
        value=StatusEnum.closed.value
    )
    
    db.add(ticket)
    db.add(log)
    
    db.commit()
    
    db.refresh(ticket)
    
    return ticket    