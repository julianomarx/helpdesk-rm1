from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from models import Ticket as TicketModel, Team as TeamModel, TicketLog as TicketLogModel
from models import User as UserModel, Category as CategoryModel
from models import LogActionEnum
from schemas import TicketCreate, TicketUpdate as TicketSchema, TicketOut, TicketUpdate, TicketWithComments
from schemas import StatusEnum, ProgressEnum

from models import RoleEnum

from services.ticket_logs import FIELD_TO_ACTION
from services.permissions import validate_field_permission
from services.authorization import ensure_can_assign_agent, ensure_user_can_access_ticket
from services.ticket_service import assign_agent_to_ticket, ensure_agent_belongs_to_ticket_assigned_team
from services.ticket_service import start_ticket_service, create_ticket_service, list_tickets_service

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
    
    if not ensure_user_can_access_ticket(ticket, current_user):
        raise HTTPException(status_code=403, detail="Acesso negado ao Ticket")
    
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
    
    if not ensure_user_can_access_ticket(ticket, current_user):
        raise HTTPException(status_code=403, detail="Acesso negado ao ticket")
    
    
    logs = []
    
    data = ticket_update.model_dump(exclude_unset=True)
    
    for field, new_value in data.items():
        
        if not validate_field_permission(current_user.role, field):
            raise HTTPException(
                status_code=403,
                detail=f"Você não tem permissão para alterar o campo '{field}'"
            )
        
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

@router.put("/start-ticket/{ticket_id}", response_model=TicketOut)
def start_ticket(
    ticket_id: int,
    db: Session = Depends(get_db), 
    current_user: UserModel = Depends(get_current_user),
):
    
    ticket = db.query(TicketModel).filter(TicketModel.id == ticket_id).first()
    
    if not ticket:
        raise HTTPException(status_code=404,detail="Ticket not found")
    
    ensure_can_assign_agent(ticket, current_user, current_user, db)
    
    ensure_agent_belongs_to_ticket_assigned_team(ticket, current_user)
    
    #verifica se ja não tem alguém atendendo 
    if ticket.assigned_to is not None:
        raise HTTPException(status_code=400, detail="This ticket is already being handled by another agent")
    
    start_ticket_service(ticket.id, current_user, db)
    
    db.commit()
    db.refresh(ticket)
    
    return ticket   

@router.put("/close-ticket/{ticket_id}", response_model=TicketOut)
def close_ticket(ticket_id: int, db: Session = Depends(get_db), current_user: UserModel = Depends(get_current_user)):
    
    ticket = db.query(TicketModel).filter(TicketModel.id == ticket_id).first()
    
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket não localizado")
    
    #Checar permissão 
    if not ensure_user_can_access_ticket(ticket, current_user):
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

@router.put("/reopen-ticket/{ticket_id}", response_model=TicketOut)
def reopen_ticket(ticket_id: int, db: Session = Depends(get_db), current_user: UserModel = Depends(get_current_user)):
    
    ticket = db.query(TicketModel).filter(TicketModel.id == ticket_id).first()
    
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket não localizado")
    
    if not ensure_user_can_access_ticket(ticket, current_user):
        raise HTTPException(status_code=404, detail="Acesso negado ao ticket")
    
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
    
    if not ensure_user_can_access_ticket(ticket_id, current_user):
        raise HTTPException(status_code=403, detail="Acesso negado ao ticket")
    
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
    
    if not ensure_user_can_access_ticket(ticket, current_user):
        raise HTTPException(status_code=403, detail="Acesso negado ao ticket")
    
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

