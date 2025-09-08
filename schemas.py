from pydantic import BaseModel, Field, EmailStr
from typing import Optional
from enum import Enum

#Enums Pydantic
class PriorityEnum(str, Enum):
    low = "low"
    medium = "medium"
    high = "high"

class StatusEnum(str, Enum):
    open = "open"
    in_progress = "in_progress"
    closed = "closed"

class RoleEnum(str, Enum):
    admin = "admin"
    agent = "agent"
    client_manager = "client_manager"
    client_receptionist = "client_receptionist"

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    sub: str | None = None
    
# Modelos de Usuários - ENTRADA E SAÍDA 
class UserCreate(BaseModel):
    name: str = Field(..., example="Juliano")
    email: EmailStr = Field(..., example="email@gmail.com")
    password: str = Field(..., example="password")
    role: RoleEnum = Field(..., example="client_manager")

class UserUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[EmailStr] = None
    password: Optional[str] = None
    role: Optional[RoleEnum] = None

class User(BaseModel):
    id: int
    name: str
    email: EmailStr
    role: RoleEnum

    class Config:
        from_attributes = True  # permite converter ORM → Schema

# Modelos de Hotel - ENTRADA E SAÍDA  
class HotelBase(BaseModel):
    code : str = Field(..., example="HXXXX")
    name : str = Field(..., example="Hotel Ibis Canoas Shopping")

class Hotel(HotelBase):
    id : int = Field(..., example=1)

    class Config:
        from_attributes = True  # permite converter ORM → Schema

# Modelos de Tickets - ENTRADA E SAÍDA 
class TicketCreate(BaseModel):
    title: str = Field(..., example="Computador da recepção não está imprimindo")
    description: str = Field(..., example="Descrição do chamado")
    priority: PriorityEnum = Field(PriorityEnum.low, example="low")
    status: StatusEnum = StatusEnum.open #default sempre Open
    created_by: int = Field(..., example=1)
    assigned_to: Optional[int] = Field(None, example=1)

class Ticket(TicketCreate):
    id: int

    class Config:
        from_attributes = True

# Modelos de Comentários - ENTRADA E SAÍDA 
class CommentCreate(BaseModel):
    ticket_id: int = Field(..., example=1)
    user_id: int = Field(..., example=1)
    comment: str = Field(..., example="Poderiam nos dar mais detalhes do erro?")

class Comment(CommentCreate):
    id: int

    class Config: 
        from_attributes = True