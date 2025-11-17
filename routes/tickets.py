from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from models import Ticket as TicketModel, Team as TeamModel, TicketLog as TicketLogModel
from models import User as UserModel, Category as CategoryModel
from schemas import TicketCreate, Ticket, TicketUpdate as TicketSchema, TicketOut, TicketUpdate, TicketWithComments
from schemas import StatusEnum, ProgressEnum

from models import LogActionEnum

from database import get_db
from auth_utils import get_current_user

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
    
    comments = ticket.comments
    
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