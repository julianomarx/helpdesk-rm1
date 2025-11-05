from enum import Enum as PyEnum
from sqlalchemy import Enum as SAEnum
from sqlalchemy import Column, Integer, String, TIMESTAMP, ForeignKey, Text, DateTime
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
    done = "done"

class StatusEnum(str, PyEnum):
    open = "open"
    closed = "closed"

class PriorityEnum(str, PyEnum):
    low = "low"
    medium = "medium"
    high = "high"
    
class LogActionEnum(str, PyEnum):
    created = "created"
    status_changed = "status_changed"
    assigned_changed = "assigned_changed"
    priority_changed = "priority_changed"
    team_changed = "team_changed"

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
    role = Column(SAEnum(RoleEnum), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    #relacionamentos
    created_tickets = relationship("Ticket", back_populates="creator", foreign_keys="Ticket.created_by")
    assigned_tickets = relationship("Ticket", back_populates="assignee", foreign_keys="Ticket.assigned_to")
    comments = relationship("TicketComment", back_populates="author", cascade="all, delete-orphan")
    hotels = relationship("UserHotel", back_populates="user", cascade="all, delete-orphan")
    logs = relationship("TicketLog", back_populates="user", cascade="all, delete-orphan")
    teams = relationship("UserTeam", back_populates="user")

class Ticket(Base):
    __tablename__ = "tickets"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(100), nullable=False)
    description = Column(Text, nullable=False)
    status = Column(SAEnum(StatusEnum), nullable=False, default=StatusEnum.open)
    progress = Column(SAEnum(ProgressEnum), nullable=False, default=ProgressEnum.waiting)
    priority = Column(SAEnum(PriorityEnum), nullable=False, default=PriorityEnum.low)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    assigned_to = Column(Integer, ForeignKey("users.id"), nullable=True)
    hotel_id = Column(Integer, ForeignKey("hotels.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    assigned_team_id = Column(Integer, ForeignKey("teams.id"), nullable=True)

    #relacionamentos bidirecionais
    creator = relationship("User", back_populates="created_tickets", foreign_keys=[created_by])
    assignee = relationship("User", back_populates="assigned_tickets", foreign_keys=[assigned_to])
    hotel = relationship("Hotel", back_populates="tickets")
    logs = relationship("TicketLog", back_populates="ticket", cascade="all, delete-orphan")
    comments = relationship("TicketComment", back_populates="ticket", cascade="all, delete-orphan")
    assigned_team = relationship("Team", back_populates="tickets")

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
    
class UserTeam(Base):
    __tablename__ = "user_teams"
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    team_id = Column(Integer, ForeignKey("teams.id"), nullable=False)
    
    user = relationship("User", back_populates="teams")
    team = relationship("Team", back_populates="users")