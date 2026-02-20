from fastapi import HTTPException

from models import TicketLog as TicketLogModel, LogActionEnum
from models import Ticket as TicketModel, User as UserModel
from models import Category as CategoryModel, SubCategory as SubCategoryModel
from models import Hotel as HotelModel
from models import ProgressEnum, StatusEnum, RoleEnum

from schemas import TicketCreate
from services.authorization import ensure_can_assign_agent, ensure_user_can_access_hotel
from sqlalchemy.orm import Session

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
    
    db.commit()
    
    db.refresh(ticket)
    
    return ticket

def create_ticket_service(
    ticket_to_create: TicketCreate, 
    current_user: UserModel, 
    db: Session
):
    
    hotel = db.query(HotelModel).filter(HotelModel.id == ticket_to_create.hotel_id).first()
    if not hotel:
        raise HTTPException(status_code=404, detail="Hotel not found")
    
    if not ensure_user_can_access_hotel(current_user, hotel):
        raise HTTPException(status_code=403, detail="Access to this hotel is unauthorized for your user")
        
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
    
    return db_ticket

def list_tickets_service(
    current_user: UserModel,
    db: Session
):
    query = db.query(TicketModel)
    
    if current_user.role == RoleEnum.admin:
        pass
    
    elif current_user.role == RoleEnum.agent:
        user_team_ids = {ut.team_id for ut in current_user.teams}
        user_hotel_ids = {uh.hotel_id for uh in current_user.hotels}
        
        query = query.filter(
            TicketModel.assigned_team_id.in_(user_team_ids),
            TicketModel.hotel_id.in_(user_hotel_ids)
        )
        
    elif current_user.role in [
        RoleEnum.client_manager,
        RoleEnum.client_receptionist
    ]:
        user_hotel_ids = {uh.hotel_id for uh in current_user.hotels}
        query = query.filter(
            TicketModel.hotel_id.in_(user_hotel_ids)
        )
        
    else:
        query = query.filter(False)  
    
    return query.all()