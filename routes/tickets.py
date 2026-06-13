from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from models import Ticket as TicketModel, Team as TeamModel, TicketLog as TicketLogModel
from models import User as UserModel, Category as CategoryModel
from models import LogActionEnum, ProgressEnum as ProgressEnumModel
from schemas import TicketCreate, TicketUpdate as TicketSchema, TicketOut, TicketUpdate, TicketWithComments, SubcategoryUpdate, TicketListOut
from schemas import StatusEnum, ProgressEnum, ScheduleVisitInput

from models import RoleEnum

from services.permissions import can_update_ticket_field
from services.authorization import ensure_can_assign_agent, ensure_user_can_access_ticket
from services.ticket_service import assign_agent_to_ticket, ensure_agent_belongs_to_ticket_assigned_team
from services.notification_service import create_notification
from services.ticket_service import start_ticket_service, create_ticket_service, list_tickets_service, ticket_edit_service, assign_ticket_team_service, cancel_ticket_service
from services.ticket_service import  close_ticket_service, update_ticket_subcategory_service, reopen_ticket_service, return_ticket_to_queue_service, get_ticket_service      

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

@router.get("/", response_model=TicketListOut)
def list_tickets(
    page: int = Query(
        default=1,
        ge=1
    ),

    page_size: int = Query(
        default=50,
        ge=1,
        le=100
    ),

    status: str = Query(
        default="open"
    ),

    search: str | None = Query(
        default=None
    ),

    progress: str | None = Query(
        default=None
    ),

    priority: str | None = Query(
        default=None
    ),

    team_id: int | None = Query(
        default=None
    ),

    category_id: int | None = Query(
        default=None
    ),

    subcategory_id: int | None = Query(
        default=None
    ),

    hotel_id: int | None = Query(
        default=None
    ),

    db: Session = Depends(get_db),

    current_user: UserModel = Depends(
        get_current_user
    )
):

    return list_tickets_service(
        current_user=current_user,
        db=db,

        page=page,
        page_size=page_size,

        status=status,

        search=search,
        progress=progress,
        priority=priority,

        team_id=team_id,

        category_id=category_id,
        subcategory_id=subcategory_id,

        hotel_id=hotel_id
    )

@router.get("/{ticket_id}", response_model=TicketWithComments)
def get_ticket(ticket_id: int, db: Session = Depends(get_db), current_user: UserModel = Depends(get_current_user)):
    
    ticket = get_ticket_service(ticket_id, current_user,db)
    
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

    # Notifica o criador do chamado que o atendimento foi iniciado (se não for ele mesmo)
    if ticket.created_by and ticket.created_by != current_user.id:
        create_notification(
            db,
            user_id=ticket.created_by,
            type="ticket_started",
            title=f"Atendimento iniciado no chamado #{ticket.id}",
            body=f'"{ticket.title}" está sendo atendido por {current_user.name}',
            ticket_id=ticket.id,
        )

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
def reopen_ticket(
    ticket_id: int, 
    db: Session = Depends(get_db), 
    current_user: UserModel = Depends(get_current_user)
):

    ticket = reopen_ticket_service(ticket_id, current_user, db)
    
    return ticket  

@router.put("/return-ticket/{ticket_id}")
def return_ticket(
    ticket_id: int, 
    current_user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db)
):                 
    
    ticket = return_ticket_to_queue_service(ticket_id, current_user, db)

    return ticket

@router.delete("/delete-ticket/{ticket_id}")
def delete_ticket(ticket_id: int, db: Session = Depends(get_db), current_user: UserModel = Depends(get_current_user)):
    ticket = db.query(TicketModel).filter(TicketModel.id == ticket_id).first()
    
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket não localizado")
    
    ensure_user_can_access_ticket(ticket_id, current_user, db)
    
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
    
    ensure_user_can_access_ticket(ticket, current_user, db)
    
    target_user = db.query(UserModel).filter(UserModel.id == user_id).first()
    
    if not target_user:
        raise HTTPException(status_code=404, detail="Usuário não localizado")
    
    ensure_can_assign_agent(ticket, current_user, target_user, db)
    
    ensure_agent_belongs_to_ticket_assigned_team(ticket, target_user)
    
    if ticket.assigned_to == target_user.id:
        return ticket
    
    if ticket.progress == ProgressEnum.waiting.value:
        raise HTTPException(status_code=401, detail="Não se pode transferir chamados que ainda estão aguardando atendimento")
    
    assign_agent_to_ticket(ticket, current_user, target_user, db)

    # Notifica o novo responsável (se não for ele mesmo que está atribuindo)
    if target_user.id != current_user.id:
        create_notification(
            db,
            user_id=target_user.id,
            type="ticket_assigned",
            title=f"Chamado #{ticket.id} atribuído a você",
            body=f'"{ticket.title}" foi direcionado por {current_user.name}',
            ticket_id=ticket.id,
        )

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


@router.put("/{ticket_id}/schedule-visit", response_model=TicketOut)
def schedule_visit(
    ticket_id: int,
    payload: ScheduleVisitInput,
    current_user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if current_user.role not in (RoleEnum.admin, RoleEnum.agent):
        raise HTTPException(status_code=403, detail="Acesso negado")

    ticket = db.query(TicketModel).filter(TicketModel.id == ticket_id).first()
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket não encontrado")

    prev_date = ticket.scheduled_visit_at
    ticket.scheduled_visit_at = payload.scheduled_at
    ticket.progress = ProgressEnumModel.scheduled_visit

    action = "visit_rescheduled" if prev_date else "visit_scheduled"
    log = TicketLogModel(
        ticket_id=ticket.id,
        user_id=current_user.id,
        action=action,
        value=payload.scheduled_at.isoformat(),
    )
    db.add(log)
    db.commit()
    db.refresh(ticket)
    return ticket
