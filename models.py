from enum import Enum as PyEnum
from sqlalchemy import Enum as SAEnum
from sqlalchemy import Boolean, Column, Integer, String, TIMESTAMP, ForeignKey, Text, DateTime, UniqueConstraint
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from database import Base

class RoleEnum(str, PyEnum):
    admin = "admin"
    agent = "agent"
    client_manager = "client_manager"
    client_receptionist = 'client_receptionist'

class ProgressEnum(str, PyEnum):
    waiting = "waiting"
    in_progress = "in_progress"
    feedback = "feedback"
    awaiting_confirmation = "awaiting_confirmation"
    scheduled_visit = "scheduled_visit"
    done = "done"

class StatusEnum(str, PyEnum):
    open = "open"
    closed = "closed"
    cancelled = "cancelled"

class PriorityEnum(str, PyEnum):
    low = "low"
    medium = "medium"
    high = "high"
    
class LogActionEnum(str, PyEnum):
    # Ticket lifecycle
    created = "created"                             #feito
    ticket_started = "ticket_started"               #Feito
    ticket_closed = "ticket_closed"                 #Feito 
    ticket_reopened = "ticket_reopened"             #fazendo 
    ticket_deleted = "ticket_deleted"               #Algo que foi deletado não tem como ter log
    ticket_cancelled = "ticket_cancelled" 
    ticket_returned = "ticket_returned"          

    # Core changes
    status_changed = "status_changed"
    progress_changed = "progress_changed"           
    assigned_changed = "assigned_changed"
    priority_changed = "priority_changed"
    team_changed = "team_changed"                   #feito
    category_changed = "category_changed"
    subcategory_changed = "subcategory_changed"     

    # Comments
    comment_updated = "comment_updated"
    comment_deleted = "comment_deleted"
    
    # Agent join
    agent_joined = "agent_joined"    # quando um segundo agente entra no ticket
    agent_left = "agent_left"        # quando é removido

    # Time tracking
    time_started = "time_started"
    time_paused = "time_paused"
    time_resumed = "time_resumed"
    time_stopped = "time_stopped"

    # SLA (opcional, mas MUITO útil)
    sla_started = "sla_started"
    sla_paused = "sla_paused"
    sla_resumed = "sla_resumed"
    sla_breached = "sla_breached"
    sla_stopped = "sla_stopped"

class Hotel(Base):
    __tablename__ = "hotels"

    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(10), unique=True, index=True, nullable=False)
    name = Column(String(100), nullable=False)

    #relação com hotel.tickets
    tickets = relationship("Ticket", back_populates="hotel", cascade="all, delete-orphan")
    users = relationship("UserHotel", back_populates="hotel", cascade="all, delete-orphan")

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    email = Column(String(100), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    role = Column(SAEnum(RoleEnum, native_enum=False), nullable=False)
    avatar_url = Column(String(255), nullable=True)
    last_seen_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    #relacionamentos
    created_tickets = relationship("Ticket", back_populates="creator", foreign_keys="Ticket.created_by")
    assigned_tickets = relationship("Ticket", back_populates="assignee", foreign_keys="Ticket.assigned_to")
    comments = relationship("TicketComment", back_populates="author", cascade="all, delete-orphan")
    hotels = relationship("UserHotel", back_populates="user", cascade="all, delete-orphan")
    logs = relationship("TicketLog", back_populates="user", cascade="all, delete-orphan")
    teams = relationship("UserTeam", back_populates="user")
    todos_created = relationship("Todo", back_populates="creator", foreign_keys="Todo.creator_id")
    todos_assigned = relationship("Todo", back_populates="assignee", foreign_keys="Todo.assignee_id")
    mural_posts = relationship("MuralPost", back_populates="author", cascade="all, delete-orphan")
    mural_comments = relationship("MuralComment", back_populates="author", cascade="all, delete-orphan")
    mural_acks = relationship("MuralAck", back_populates="user", cascade="all, delete-orphan")

class Ticket(Base):
    __tablename__ = "tickets"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(100), nullable=False)
    description = Column(Text, nullable=False)
    status = Column(SAEnum(StatusEnum, native_enum=False),nullable=False,default=StatusEnum.open)
    progress = Column(
    SAEnum(ProgressEnum, native_enum=False),
    nullable=False,
    default=ProgressEnum.waiting
)
    priority = Column(
    SAEnum(PriorityEnum, native_enum=False),
    nullable=False,
    default=PriorityEnum.low
)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    assigned_to = Column(Integer, ForeignKey("users.id"), nullable=True)
    hotel_id = Column(Integer, ForeignKey("hotels.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    assigned_team_id = Column(Integer, ForeignKey("teams.id"), nullable=True)
    category_id = Column(Integer, ForeignKey("categories.id"), nullable=True)
    subcategory_id = Column(Integer, ForeignKey("subcategories.id"), nullable=True)
    scheduled_visit_at = Column(DateTime(timezone=True), nullable=True)

    #relacionamentos bidirecionais
    creator = relationship("User", back_populates="created_tickets", foreign_keys=[created_by])
    assignee = relationship("User", back_populates="assigned_tickets", foreign_keys=[assigned_to])
    hotel = relationship("Hotel", back_populates="tickets")
    logs = relationship("TicketLog", back_populates="ticket", cascade="all, delete-orphan")
    comments = relationship("TicketComment", back_populates="ticket", cascade="all, delete-orphan")
    assigned_team = relationship("Team", back_populates="tickets")
    category = relationship("Category", back_populates="tickets")
    subcategory = relationship("SubCategory", back_populates="tickets")
    attachments = relationship("Attachment", back_populates="ticket", cascade="all, delete-orphan")
    sla = relationship("TicketSLA", back_populates="ticket", uselist=False, cascade="all, delete-orphan")
    
class Category(Base):
    __tablename__ = "categories"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), nullable=False)
    team_id = Column(Integer, ForeignKey("teams.id"), nullable=False)
    
    team = relationship("Team", back_populates="categories")
    tickets = relationship("Ticket", back_populates="category")
    subcategories = relationship("SubCategory", back_populates="category", cascade="all, delete-orphan")

class SubCategory(Base):
    __tablename__ = "subcategories"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(150), nullable=False)
    category_id = Column(Integer, ForeignKey("categories.id"), nullable=False)
    sla_policy_id = Column(Integer, ForeignKey("sla_policies.id"), nullable=True)

    tickets = relationship("Ticket", back_populates="subcategory")
    category = relationship("Category", back_populates="subcategories")
    sla_policy = relationship("SLAPolicy", back_populates="subcategories")
   

class TicketComment(Base):
    __tablename__ = "ticket_comments"

    id = Column(Integer, primary_key=True, index=True)
    ticket_id = Column(Integer, ForeignKey("tickets.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    comment = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    ticket = relationship("Ticket", back_populates="comments")
    author = relationship("User", back_populates="comments")
    
class TicketLog(Base):
    __tablename__ = "ticket_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    ticket_id = Column(Integer, ForeignKey("tickets.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    action = Column(String(50), nullable=False)
    value = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    ticket = relationship("Ticket", back_populates="logs")
    user = relationship("User", back_populates="logs")
    
class TicketTimeLog(Base):
    __tablename__ = 'ticket_timelogs'
    
    id = Column(Integer, primary_key=True)
    ticket_id = Column(Integer, ForeignKey("tickets.id"))
    user_id = Column(Integer, ForeignKey("users.id"))
    
    start_time = Column(DateTime, nullable=False) #quando começa o cronometro
    end_time = Column(DateTime, nullable=True) #quando terminou 
    
    # tempo calculado (em segundos)
    total_seconds = Column(Integer, default=0)

class UserHotel(Base):
    __tablename__ = "user_hotels"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    hotel_id = Column(Integer, ForeignKey("hotels.id"), nullable=False)

    user = relationship("User", back_populates="hotels")
    hotel = relationship("Hotel", back_populates="users")
    
class Team(Base):
    __tablename__ = "teams"
    
    id = Column(Integer, primary_key=True)
    name = Column(String(50), unique=True, nullable=False)
    
    users = relationship("UserTeam", back_populates="team", cascade="all, delete-orphan")
    tickets = relationship("Ticket", back_populates="assigned_team")
    categories = relationship("Category", back_populates="team")
    
class UserTeam(Base):
    __tablename__ = "user_teams"
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    team_id = Column(Integer, ForeignKey("teams.id"), nullable=False)
    
    user = relationship("User", back_populates="teams")
    team = relationship("Team", back_populates="users")
    
class SLAPolicy(Base):
    __tablename__ = "sla_policies"

    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False, unique=True)
    description = Column(Text, nullable=True)
    first_response_hours = Column(Integer, nullable=False)
    resolution_hours = Column(Integer, nullable=False)
    priority = Column(SAEnum(PriorityEnum, native_enum=False), nullable=False, default=PriorityEnum.medium)

    subcategories = relationship("SubCategory", back_populates="sla_policy")
    ticket_sla_records = relationship("TicketSLA", back_populates="policy")


class TicketSLA(Base):
    __tablename__ = "ticket_sla"

    id = Column(Integer, primary_key=True)
    ticket_id = Column(Integer, ForeignKey("tickets.id", ondelete="CASCADE"), nullable=False, unique=True)
    policy_id = Column(Integer, ForeignKey("sla_policies.id"), nullable=True)

    # Snapshots da política no momento da aplicação
    first_response_hours = Column(Integer, nullable=False)
    resolution_hours = Column(Integer, nullable=False)

    # Ponto de partida do relógio SLA (= ticket.created_at)
    started_at = Column(DateTime(timezone=True), nullable=False)

    # Deadlines calculados
    response_deadline = Column(DateTime(timezone=True), nullable=False)
    resolution_deadline = Column(DateTime(timezone=True), nullable=False)

    # Quando foram cumpridos (None = não cumprido)
    response_met_at = Column(DateTime(timezone=True), nullable=True)
    resolution_met_at = Column(DateTime(timezone=True), nullable=True)

    # Controle de pausa (progress = feedback)
    paused_at = Column(DateTime(timezone=True), nullable=True)
    total_paused_seconds = Column(Integer, default=0, nullable=False)

    # Flags de violação
    response_breached = Column(Boolean, default=False, nullable=False)
    resolution_breached = Column(Boolean, default=False, nullable=False)

    ticket = relationship("Ticket", back_populates="sla")
    policy = relationship("SLAPolicy", back_populates="ticket_sla_records")


class Notification(Base):
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    type = Column(String(50), nullable=False)
    title = Column(String(255), nullable=False)
    body = Column(Text, nullable=True)
    ticket_id = Column(Integer, ForeignKey("tickets.id", ondelete="CASCADE"), nullable=True)
    mural_post_id = Column(Integer, ForeignKey("mural_posts.id", ondelete="SET NULL"), nullable=True)
    read = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User")
    ticket = relationship("Ticket")
    mural_post = relationship("MuralPost")


class Attachment(Base):
    __tablename__ = "attachments"
    
    id = Column(Integer, primary_key=True)
    
    ticket_id = Column(Integer, ForeignKey("tickets.id", ondelete="CASCADE"), nullable=False)
    
    file_name = Column(String(255), nullable=False)
    stored_name = Column(String(255), nullable=False)
    
    mime_type = Column(String(100))
    file_size = Column(Integer)
    
    uploaded_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    #relacionamento
    ticket = relationship("Ticket", back_populates="attachments")
    uploader = relationship("User")


class Todo(Base):
    __tablename__ = "todos"

    id = Column(Integer, primary_key=True)
    creator_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    assignee_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    body = Column(Text, nullable=False)
    done = Column(Boolean, default=False, nullable=False)
    done_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    creator = relationship("User", back_populates="todos_created", foreign_keys=[creator_id])
    assignee = relationship("User", back_populates="todos_assigned", foreign_keys=[assignee_id])


class MuralPost(Base):
    __tablename__ = "mural_posts"

    id = Column(Integer, primary_key=True)
    author_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    body = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    author = relationship("User", back_populates="mural_posts")
    comments = relationship("MuralComment", back_populates="post", cascade="all, delete-orphan", order_by="MuralComment.created_at")
    acks = relationship("MuralAck", back_populates="post", cascade="all, delete-orphan")


class MuralComment(Base):
    __tablename__ = "mural_comments"

    id = Column(Integer, primary_key=True)
    post_id = Column(Integer, ForeignKey("mural_posts.id", ondelete="CASCADE"), nullable=False)
    author_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    body = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    post = relationship("MuralPost", back_populates="comments")
    author = relationship("User", back_populates="mural_comments")


class MuralAck(Base):
    __tablename__ = "mural_acks"

    id = Column(Integer, primary_key=True)
    post_id = Column(Integer, ForeignKey("mural_posts.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (UniqueConstraint("post_id", "user_id", name="uq_mural_ack"),)

    post = relationship("MuralPost", back_populates="acks")
    user = relationship("User", back_populates="mural_acks")