from pydantic import BaseModel, Field, EmailStr
from typing import Optional, List
from datetime import datetime
from enum import Enum

# Enums
class PriorityEnum(str, Enum):
    low = "low"
    medium = "medium"
    high = "high"

class StatusEnum(str, Enum):
    open = "open"
    closed = "closed"
    cancelled = "cancelled"

class ProgressEnum(str, Enum):
    waiting = "waiting"
    in_progress = "in_progress"
    feedback = "feedback"
    awaiting_confirmation = "awaiting_confirmation"
    done = "done"

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
    
class UserCreateWithHotels(BaseModel):
    name: str
    email: EmailStr
    password: str
    role: RoleEnum
    hotel_ids: Optional[List[int]] = []

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
        

class UserHotelsUpdate(BaseModel):
    hotel_ids: List[int]


class UserHotelOut(BaseModel):
    id: int
    hotel: Hotel

    class Config:
        from_attributes = True

class UserOut(User):
    hotels: List[UserHotelOut] = []
    
    
# --------------------
# COMENTÁRIOS
# --------------------
class CommentCreate(BaseModel):
    ticket_id: int
    user_id: int
    comment: str

class Comment(CommentCreate):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True

class CommentOut(Comment):
    author: User
    
# --------------------
# TEAMS
# --------------------
class TeamBase(BaseModel):
    name: str

class Team(TeamBase):
    id: int

    class Config:
        from_attributes = True
        
        
# --------------------
# Category
# --------------------
        
class CategoryBase(BaseModel):
    name: str
    team_id: int
    
class CategoryCreate(CategoryBase):
    pass

class CategoryUpdate(BaseModel):
    name: Optional[str] = None
    team_id: Optional[int] = None

class Category(CategoryBase):
    id: int

    class Config:
        from_attributes = True
        
        
# --------------------
# Sub-categories
# --------------------

class SubCategoryBase(BaseModel):
    name: str
    category_id: int

class SubCategoryCreate(SubCategoryBase):
    pass

class SubCategoryUpdate(BaseModel):
    name: Optional[str] = None
    category_id: Optional[int] = None

class SubCategory(SubCategoryBase):
    id: int

    class Config:
        from_attributes = True

class CategoryWithSubcategories(Category):
    subcategories: List[SubCategory] = []


# --------------------
# TICKETS
# --------------------
class TicketCreate(BaseModel):
    title: str
    description: str
    priority: PriorityEnum = PriorityEnum.low
    hotel_id: int
    category_id: int
    subcategory_id: int

class TicketUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    priority: Optional[PriorityEnum] = None
    status: Optional[StatusEnum] = None
    progress: Optional[ProgressEnum] = None  
    assigned_to: Optional[int] = None
    category_id: Optional[int] = None
    subcategory_id: Optional[int] = None
    hotel_id: Optional[int] = None

class Ticket(TicketCreate):
    id: int
    created_at: datetime
    updated_at: datetime
    progress: ProgressEnum = ProgressEnum.waiting
    status: StatusEnum = StatusEnum.open
    assigned_team_id: int

    class Config:
        from_attributes = True

class TicketOut(Ticket):
    hotel: Hotel
    creator: User
    assignee: Optional[User] = None
    assigned_team: Optional[Team] = None
    category: Optional[Category] = None
    subcategory: Optional[SubCategory] = None


class TicketWithComments(TicketOut):  
    comments: List[CommentOut] = []

class TimeLogBase(BaseModel):
    ticket_id: int
    user_id: int
    
class TimeLogCreate(TimeLogBase):
    pass

class TimeLogPause(BaseModel):
    timelog_id: int
    
class TimeLogResponse(TimeLogBase):
    id: int
    start_time: datetime
    end_time: datetime | None
    total_seconds: int
    
    class Config:
        orm_mode = True
        
class TicketLogOut(BaseModel):
    id: int
    action: str
    value: Optional[str]
    created_at: datetime
    user: Optional[User]

    class Config:
        from_attributes = True