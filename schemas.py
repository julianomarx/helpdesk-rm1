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
    client = "client"


# Modelos de Usuários - ENTRADA E SAÍDA 
class UserCreate(BaseModel):
    name: str = Field(..., example="Juliano")
    email: EmailStr = Field(..., example="email@example.com.br")
    password: str = Field(..., example="StrongPassword@123456")
    role: RoleEnum = Field(..., example="client")

class UserUpdate(BaseModel):
    name: Optional[str] = Field(None, example="Juliano")
    email: Optional[EmailStr] = Field(None, example="Juliano@example.com.br")
    password: Optional[str] = Field(None, example="password")
    role: Optional[RoleEnum] = Field(None, example="client")

class User(BaseModel):
    id: int
    name: str
    email: EmailStr
    role: RoleEnum

    class Config:
        from_attributes = True  # permite converter ORM → Schema
    
# Modelos de Tickets - ENTRADA E SAÍDA 
class TicketCreate(BaseModel):
    title: str = Field(..., example="Computador da recepção não está imprimindo")
    description: str = Field(..., example="Boa tarde, o computador W-H5670-FO4 não está mais imprimindo. Poderiam verificar por favor?")
    priority: PriorityEnum = Field(PriorityEnum.low, example="low")
    status: StatusEnum = Field(StatusEnum.open, example="open") #preciso mudar aqui pra sempre abrir como Open
    created_by: int = Field(..., example=1)
    assigned_to: Optional[int] = None

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