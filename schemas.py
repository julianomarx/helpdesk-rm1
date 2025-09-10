from pydantic import BaseModel, Field, EmailStr
from typing import Optional, List
from enum import Enum

# Enums
class PriorityEnum(str, Enum):
    low = "low"
    medium = "medium"
    high = "high"

class StatusEnum(str, Enum):
    open = "open"
    in_progress = "in_progress"
    closed = "closed"
    awaiting_confirmation = "awaiting_confirmation"

class RoleEnum(str, Enum):
    admin = "admin"
    agent = "agent"
    client_manager = "client_manager"
    client_receptionist = "client_receptionist"

# Token
class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    sub: Optional[str] = None

# --------------------
# HOTÉIS
# --------------------
class HotelBase(BaseModel):
    code: str = Field(..., example="H8273")
    name: str = Field(..., example="Hotel Ibis Canoas Shopping")

class HotelCreate(HotelBase):
    pass

class Hotel(HotelBase):
    id: int

    class Config:
        from_attributes = True

# --------------------
# USUÁRIOS
# --------------------
class UserCreate(BaseModel):
    name: str
    email: EmailStr
    password: str
    role: RoleEnum

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
        from_attributes = True

class UserHotelOut(BaseModel):
    id: int
    hotel: Hotel

    class Config:
        from_attributes = True

class UserOut(User):
    hotels: List[UserHotelOut] = []

# --------------------
# TICKETS
# --------------------
class TicketCreate(BaseModel):
    title: str
    description: str
    priority: PriorityEnum = PriorityEnum.low
    status: StatusEnum = StatusEnum.open
    created_by: int
    assigned_to: Optional[int] = None
    hotel_id: int

class TicketUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    priority: Optional[PriorityEnum] = None
    status: Optional[StatusEnum] = None
    assigned_to: Optional[int] = None

class Ticket(TicketCreate):
    id: int

    class Config:
        from_attributes = True

class TicketOut(Ticket):
    hotel: Hotel
    creator: User
    assignee: Optional[User] = None

# --------------------
# COMENTÁRIOS
# --------------------
class CommentCreate(BaseModel):
    ticket_id: int
    user_id: int
    comment: str

class Comment(CommentCreate):
    id: int

    class Config:
        from_attributes = True

class CommentOut(Comment):
    author: User
