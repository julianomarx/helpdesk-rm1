from fastapi import HTTPException

from math import ceil

from models import TicketLog as TicketLogModel, LogActionEnum
from models import Ticket as TicketModel, User as UserModel
from models import Team as TeamModel, TicketSLA as TicketSLAModel

from models import Category as CategoryModel, SubCategory as SubCategoryModel
from models import Hotel as HotelModel
from models import ProgressEnum, StatusEnum, RoleEnum

from services.ticket_logs import FIELD_TO_ACTION
from services import sla_service

from schemas import TicketCreate, TicketUpdate
from services.authorization import ensure_can_assign_agent, ensure_user_can_access_hotel, ensure_user_can_access_ticket, get_user_accessible_hotel_ids, get_user_accessible_team_ids
from services.permissions import can_update_ticket_field

from sqlalchemy.orm import Session, joinedload, selectinload
from sqlalchemy import or_, cast, String

def get_ticket_service(
    ticket_id: int,
    current_user: UserModel,
    db: Session
):
    ticket = (
        db.query(TicketModel)
        .options(
            joinedload(TicketModel.hotel),
            joinedload(TicketModel.creator),
            joinedload(TicketModel.assignee),
            joinedload(TicketModel.assigned_team),
            joinedload(TicketModel.category),
            joinedload(TicketModel.subcategory),
            joinedload(TicketModel.comments),
            joinedload(TicketModel.sla).joinedload(TicketSLAModel.policy),
        )
        .filter(TicketModel.id == ticket_id)
        .first()
    )

    if not ticket:
        raise HTTPException(
            status_code=404,
            detail="Ticket not found"
        )
    
    ensure_user_can_access_ticket(ticket, current_user, db)

    return ticket


def assign_agent_to_ticket(ticket: TicketModel, current_user: UserModel, target_user: UserModel, db: Session):
    old_agent = ticket.assigned_to
    
    ticket.assigned_to = target_user.id
    
    log = TicketLogModel(
        ticket_id=ticket.id,
        user_id=current_user.id,
        action=LogActionEnum.assigned_changed.value,
        value=str(target_user.id)
    )
    
    db.add(log)
      
def ensure_agent_belongs_to_ticket_assigned_team(ticket: TicketModel, target_user: UserModel):
    
    if not ticket.assigned_team_id:
        raise HTTPException(status_code=400, detail="Ticket não possui equipe atribuida")
    
    belongs_to_team = any(
        ut.team_id == ticket.assigned_team_id
        for ut in target_user.teams
    )

    if not belongs_to_team:
        raise HTTPException(
            status_code=400,
            detail="Usuário não pertence à equipe responsável pelo ticket. Verifique se o usuário está vinculado À esta equipe"
        )
        
def start_ticket_service(
    ticket_id: int,
    current_user: UserModel,
    db: Session
):
    ticket = db.query(TicketModel).filter(TicketModel.id == ticket_id).with_for_update().first()
    
    if not ticket: 
        raise HTTPException(status_code=404, detail="Ticket não localizado")
    
    ensure_can_assign_agent(ticket, current_user, current_user, db)
    
    ensure_agent_belongs_to_ticket_assigned_team(ticket, current_user)
    
    if ticket.assigned_to is not None:
        raise HTTPException(status_code=400, detail="This ticket is already being handled by another user")
    
    ticket.assigned_to = current_user.id
    ticket.progress = ProgressEnum.in_progress.value

    log = TicketLogModel(
        ticket_id=ticket.id,
        user_id=current_user.id,
        action=LogActionEnum.ticket_started.value,
        value=None,
    )
    db.add(log)

    sla_service.mark_response_met(ticket, db)

    return ticket

def create_ticket_service(
    ticket_to_create: TicketCreate, 
    current_user: UserModel, 
    db: Session
):
    
    hotel = db.query(HotelModel).filter(HotelModel.id == ticket_to_create.hotel_id).first()
    if not hotel:
        raise HTTPException(status_code=404, detail="Hotel not found")
    
    ensure_user_can_access_hotel(current_user, hotel, db)
        
    category = db.query(CategoryModel).filter(CategoryModel.id == ticket_to_create.category_id).first()
    
    if not category:
        raise HTTPException(status_code=404, detail="Invalid category")
    
    subcategory = db.query(SubCategoryModel).filter(SubCategoryModel.id == ticket_to_create.subcategory_id).first()
    
    if not subcategory:
        raise HTTPException(status_code=404, detail="Invalid subcategory")
    
    assigned_team_id = category.team_id
    
    db_ticket = TicketModel(
        title=ticket_to_create.title,
        description=ticket_to_create.description,
        status=StatusEnum.open.value,       
        progress=ProgressEnum.waiting.value, 
        priority=ticket_to_create.priority,
        created_by=current_user.id,
        hotel_id=hotel.id,
        category_id=category.id,
        subcategory_id=subcategory.id,
        assigned_team_id=assigned_team_id
    )
    
    db.add(db_ticket)
    
    db.flush()
    
    ticket_creation_log = TicketLogModel(
        ticket_id=db_ticket.id,
        user_id=current_user.id,
        action=LogActionEnum.created.value,
        value=StatusEnum.open.value
    )
    
    ticket_team_assign_log = TicketLogModel(
        ticket_id=db_ticket.id,
        user_id=current_user.id,
        action=LogActionEnum.team_changed.value,
        value=str(assigned_team_id)
    )
    
    db.add(ticket_creation_log)
    db.add(ticket_team_assign_log)

    db.flush()
    sla_service.apply_sla_to_ticket(db_ticket, db)

    return db_ticket

def list_tickets_service(
    current_user: UserModel,
    db: Session,

    *,
    page: int = 1,
    page_size: int = 50,

    status: str = "open",

    search: str | None = None,
    progress: str | None = None,
    priority: str | None = None,

    team_id: int | None = None,

    category_id: int | None = None,
    subcategory_id: int | None = None,

    hotel_id: int | None = None
):

    query = (
        db.query(TicketModel)
        .options(

            selectinload(
                TicketModel.hotel
            ),

            selectinload(
                TicketModel.creator
            ),

            selectinload(
                TicketModel.assignee
            ),

            selectinload(
                TicketModel.assigned_team
            ),

            selectinload(
                TicketModel.category
            ),

            selectinload(
                TicketModel.subcategory
            )
        )
    )

    if current_user.role == RoleEnum.admin:

        pass

    elif current_user.role == RoleEnum.agent:

        user_team_ids = (
            get_user_accessible_team_ids(
                current_user.id,
                db
            )
        )

        user_hotel_ids = (
            get_user_accessible_hotel_ids(
                current_user.id,
                db
            )
        )

        query = query.filter(
            TicketModel.assigned_team_id.in_(
                user_team_ids
            ),
            TicketModel.hotel_id.in_(
                user_hotel_ids
            )
        )

    elif current_user.role in (
        RoleEnum.client_manager,
        RoleEnum.client_receptionist
    ):

        user_hotel_ids = (
            get_user_accessible_hotel_ids(
                current_user.id,
                db
            )
        )

        query = query.filter(
            TicketModel.hotel_id.in_(
                user_hotel_ids
            )
        )

    else:

        return {
            "items": [],
            "total": 0,
            "page": page,
            "page_size": page_size,
            "pages": 0
        }

    if status != "all":

        query = query.filter(
            TicketModel.status == status
        )

    if search:

        search = search.strip()

        query = query.filter(

            or_(

                TicketModel.title.ilike(
                    f"%{search}%"
                ),

                TicketModel.description.ilike(
                    f"%{search}%"
                ),

                cast(
                    TicketModel.id,
                    String
                ).ilike(
                    f"%{search}%"
                )
            )
        )

    if progress:

        query = query.filter(
            TicketModel.progress == progress
        )

    if priority:

        query = query.filter(
            TicketModel.priority == priority
        )

    if team_id:

        query = query.filter(
            TicketModel.assigned_team_id
            == team_id
        )

    if hotel_id:

        query = query.filter(
            TicketModel.hotel_id
            == hotel_id
        )

    if category_id:

        query = query.filter(
            TicketModel.category_id
            == category_id
        )

    if subcategory_id:

        query = query.filter(
            TicketModel.subcategory_id
            == subcategory_id
        )

    total = query.count()

    query = query.order_by(
        TicketModel.created_at.desc()
    )

    #Paginação
    query = query.offset(
        (page - 1) * page_size
    ).limit(
        page_size
    )

    tickets = query.all()

    return {

        "items": tickets,

        "total": total,

        "page": page,

        "page_size": page_size,

        "pages": ceil(
            total / page_size
        ) if total else 0
    }

def ticket_edit_service(    
    ticket_id: int, 
    ticket_update: TicketUpdate,
    current_user: UserModel,
    db: Session
):
    
    ticket = db.query(TicketModel).filter(TicketModel.id == ticket_id).with_for_update().first()
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket não localizado")
    
    ensure_user_can_access_ticket(ticket, current_user, db)
    
    logs = []
    
    update_fields = ticket_update.model_dump(exclude_unset=True)
    
    for field, new_value in update_fields.items():
        
        if not can_update_ticket_field(current_user.role, field):
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

    # Hooks SLA baseados em mudança de progress
    new_progress = update_fields.get("progress")
    if new_progress:
        if new_progress == ProgressEnum.feedback.value:
            sla_service.pause_sla(ticket, db)
        elif new_progress == ProgressEnum.in_progress.value:
            sla_service.resume_sla(ticket, db)
            sla_service.mark_response_met(ticket, db)
        elif new_progress in (ProgressEnum.awaiting_confirmation.value, ProgressEnum.done.value):
            sla_service.mark_resolution_met(ticket, db)

    return ticket

def assign_ticket_team_service(
    ticket_id: int,
    team_id: int,
    current_user: UserModel,
    db: Session
):
    
    ticket = db.query(TicketModel).filter(TicketModel.id == ticket_id).first()
    if not ticket:
        raise HTTPException(404, "Ticket não encontrado")
    
    team = db.query(TeamModel).filter(TeamModel.id == team_id).first()
    if not team:
        raise HTTPException(404, "Equipe não encontrada")
    
    ticket.assigned_team_id = team_id
    
    ticket.assigned_to = None
    
    ticket.progress = ProgressEnum.waiting.value
    
    log = TicketLogModel(
        ticket_id=ticket.id,
        user_id=current_user.id,
        action=LogActionEnum.team_changed.value,
        value=team_id
    )
    
    db.add(log)
    
    return ticket

def update_ticket_subcategory_service(
    ticket_id: int,
    subcategory_id: int,
    current_user: UserModel,
    db: Session
):
    if current_user.role not in [ RoleEnum.admin, RoleEnum.agent ]:
        raise HTTPException(status_code=403, detail="Only admins or agents can re-assign ticket's subcategory manually")
    
    ticket = db.query(TicketModel).filter(TicketModel.id == ticket_id).first()

    if not ticket:
        raise HTTPException(404, "Ticket não encontrado")
    
    subcategory = db.query(SubCategoryModel).filter(SubCategoryModel.id == subcategory_id).first()
    
    if not subcategory:
        raise HTTPException(status_code=404, detail="Subcategory not found")

    old_subcategory = ticket.subcategory_id

    ticket.subcategory_id = subcategory_id

    # Troca a categoria automaticamente quando subcategoria muda
    ticket.category_id = subcategory.category_id

    log = TicketLogModel(
        ticket_id=ticket.id,
        user_id=current_user.id,
        action=LogActionEnum.subcategory_changed.value,
        value=str(subcategory_id)
    )
    db.add(log)

    # Re-aplica SLA com a nova subcategoria (só se ticket ainda estiver aberto)
    if ticket.status == StatusEnum.open.value:
        sla_service.apply_sla_to_ticket(ticket, db)

    return ticket

def cancel_ticket_service(
    ticket_id: int,
    current_user: UserModel,
    db: Session
):
    
    ticket = db.query(TicketModel).filter(TicketModel.id == ticket_id).first()
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    
    ensure_user_can_access_ticket(ticket, current_user, db)
    
    roles_allowed_to_cancel_tickets = [ 
        RoleEnum.client_manager, RoleEnum.client_receptionist, RoleEnum.admin 
    ]
    
    if current_user.role not in roles_allowed_to_cancel_tickets:
        raise HTTPException(status_code=403, detail="Only managers or receptionist can cancell tickets")
    
    ticket.status = StatusEnum.cancelled
    
    log = TicketLogModel(
        ticket_id=ticket.id,
        user_id=current_user.id,
        action=LogActionEnum.status_changed.value,
        value=StatusEnum.cancelled.value
    )
    
    db.add(log)
    db.commit()
    
    db.refresh(ticket)
    
    return ticket

def close_ticket_service(
    ticket_id: int,
    current_user: UserModel,
    db: Session
):
    ticket = db.query(TicketModel).filter(TicketModel.id == ticket_id).first()

    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket não localizado")
    
    if ticket.progress != ProgressEnum.awaiting_confirmation.value:
        raise HTTPException(status_code=400, detail="Ticket só pode ser fechado se estiver aguardando confirmação de encerramento")
    
    if current_user.role != RoleEnum.admin:
        
        ensure_user_can_access_ticket(ticket, current_user, db) 
    
        if current_user.role == RoleEnum.agent:
            raise HTTPException(status_code=403, detail="Tickets can only be closed from the client side")
    
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

    sla_service.mark_resolution_met(ticket, db)

    db.commit()
    db.refresh(ticket)

    return ticket

def reopen_ticket_service(
    ticket_id: int,
    current_user: UserModel,
    db: Session
):
    ticket = db.query(TicketModel).filter(TicketModel.id == ticket_id).first()
    
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket não localizado")
    
    if ticket.status != StatusEnum.closed.value:
        raise HTTPException(status_code=400, detail="Apenas tickets fechados podem ser reabertos")
    
    ensure_user_can_access_ticket(ticket, current_user, db)
    
    ticket.status = StatusEnum.open.value
    ticket.progress = ProgressEnum.waiting.value
    ticket.assigned_to = None
    
    log = TicketLogModel(
        user_id=current_user.id,
        ticket_id=ticket.id,
        action=LogActionEnum.ticket_reopened.value,
        value=LogActionEnum.ticket_reopened.value
    )
    
    db.add(ticket)
    db.add(log)

    db.commit()
    db.refresh(ticket)  

    return ticket  

def return_ticket_to_queue_service(
    ticket_id: int, 
    current_user: UserModel, 
    db: Session
):
    ticket = db.query(TicketModel).filter(TicketModel.id == ticket_id).first()

    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket não localizado")

    if ticket.progress != ProgressEnum.awaiting_confirmation:
        raise HTTPException(status_code=401, detail="Apenas Tickets enviados para encerramento podem ser retornados à fila de atendimento")

    ensure_user_can_access_ticket(ticket, current_user, db)

    ticket.status = StatusEnum.open.value
    ticket.progress = ProgressEnum.waiting.value
    ticket.assigned_to = None

    log = TicketLogModel (
        user_id=current_user.id,
        ticket_id=ticket.id,
        action=LogActionEnum.ticket_returned.value,
        value=LogActionEnum.ticket_returned.value
    )

    db.add(ticket)
    db.add(log)

    db.commit()
    db.refresh(ticket)

    return ticket