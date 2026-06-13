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
    scheduled_visit = "scheduled_visit"
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
    code: Optional[str] = None
    name: Optional[str] = None

class HotelCreate(HotelBase):
    pass

class HotelUpdate(HotelBase):
    pass

class HotelOut(HotelBase):
    pass

class Hotel(HotelBase):
    id: int

    class Config:
        from_attributes = True

class HotelSimple(BaseModel):
    id: int
    code: str
    name: str

    class Config:
        from_attributes = True

# --------------------
# TEAMS
# --------------------
class TeamBase(BaseModel):
    name: str

class Team(TeamBase):
    id: int

    class Config:
        from_attributes = True

class TeamSimple(BaseModel):
    id: int
    name: str

    class Config:
        from_attributes = True
        
class SubcategoryUpdate(BaseModel):
    subcategory_id: int

class TeamSimple(BaseModel):
    id: int
    name: str

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
    
    hotel_ids: Optional[List[int]] = []
    team_ids: Optional[List[int]] = []
    
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
    avatar_url: Optional[str] = None

    class Config:
        from_attributes = True

class UserBasic(BaseModel):
    id: int
    name: str

    class Config:
        from_attributes = True
        
class UserHotelsUpdate(BaseModel):
    hotel_ids: List[int]

class UserTeamsUpdate(BaseModel):
    team_ids: List[int]


class UserHotelOut(BaseModel):
    id: int
    hotel: HotelSimple

    class Config:
        from_attributes = True

class UserOut(User):
    hotels: List[HotelSimple] = []
    teams: List[TeamSimple] = []


class UserListOut(BaseModel):

    items: list[User]
    total: int
    page: int
    page_size: int
    pages: int

    class Config:
        from_attributes = True

    
# --------------------
# COMENTÁRIOS
# --------------------
class CommentCreate(BaseModel):
    ticket_id: int
    comment: str
    
class CommentEdit(BaseModel):
    comment: str

class Comment(CommentCreate):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True

class CommentOut(Comment):
    author: UserBasic
        
        
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
# SLA POLICIES
# --------------------

class SLAPolicyCreate(BaseModel):
    name: str
    description: Optional[str] = None
    first_response_hours: int = Field(gt=0)
    resolution_hours: int = Field(gt=0)
    priority: PriorityEnum = PriorityEnum.medium

class SLAPolicyUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    first_response_hours: Optional[int] = Field(default=None, gt=0)
    resolution_hours: Optional[int] = Field(default=None, gt=0)
    priority: Optional[PriorityEnum] = None

class SLAPolicyOut(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    first_response_hours: int
    resolution_hours: int
    priority: PriorityEnum

    class Config:
        from_attributes = True

class TicketSLAOut(BaseModel):
    id: int
    policy_id: Optional[int] = None
    policy: Optional[SLAPolicyOut] = None
    first_response_hours: int
    resolution_hours: int
    started_at: datetime
    response_deadline: datetime
    resolution_deadline: datetime
    response_met_at: Optional[datetime] = None
    resolution_met_at: Optional[datetime] = None
    paused_at: Optional[datetime] = None
    total_paused_seconds: int
    response_breached: bool
    resolution_breached: bool

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
    sla_policy_id: Optional[int] = None

class SubCategory(SubCategoryBase):
    id: int
    sla_policy_id: Optional[int] = None

    class Config:
        from_attributes = True

class SubCategoryWithSLA(SubCategory):
    sla_policy: Optional[SLAPolicyOut] = None

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
    progress: Optional[ProgressEnum] = None
    category_id: Optional[int] = None
    subcategory_id: Optional[int] = None  

class Ticket(TicketCreate):
    id: int
    created_at: datetime
    updated_at: datetime
    progress: ProgressEnum = ProgressEnum.waiting
    status: StatusEnum = StatusEnum.open
    assigned_team_id: int
    scheduled_visit_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class TicketOut(Ticket):
    hotel: Hotel
    creator: UserBasic
    assignee: Optional[UserBasic] = None
    assigned_team: Optional[Team] = None
    category: Optional[Category] = None
    subcategory: Optional[SubCategory] = None
    sla: Optional[TicketSLAOut] = None

class TicketListOut(BaseModel):

    items: list[TicketOut]
    total: int
    page: int
    page_size: int
    pages: int

    class Config:
        from_attributes = True


class TicketWithComments(TicketOut):  
    comments: List[CommentOut] = []
    
    
# --------------------
# TIMELOGS
# --------------------

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
        from_attributes = True
        
class TicketLogOut(BaseModel):
    id: int
    action: str
    value: Optional[str]
    created_at: datetime
    user: Optional[UserBasic]

    class Config:
        from_attributes = True
        
# --------------------
# ATTACHMENTS
# --------------------

class AttachmentOut(BaseModel):
    id: int
    file_name: str
    mime_type: str | None
    file_size: int | None
    created_at: datetime
    url: str
    uploader: UserBasic

    class Config:
        from_attributes = True

# --------------------
# Dashboard MOdel
# --------------------

class DashboardOverview(BaseModel):

    created_today_tickets: int
    closed_today_tickets: int
    open_tickets: int
    in_progress_tickets: int
    feedback_tickets: int
    awaiting_confirmation_tickets: int
    scheduled_visit_tickets: int
    unassigned_tickets: int
    stale_48h_tickets: int
    high_priority_tickets: int


class DashboardTicketItem(BaseModel):
    id: int
    title: str
    hotel_name: str
    category_name: Optional[str] = None
    priority: str
    assignee_name: Optional[str] = None
    team_name: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    progress: str


class DashboardOperational(BaseModel):
    stale_tickets: List[DashboardTicketItem]
    unassigned_tickets: List[DashboardTicketItem]
    critical_tickets: List[DashboardTicketItem]
    awaiting_confirmation_tickets: List[DashboardTicketItem]
    feedback_tickets: List[DashboardTicketItem]


class AgentRankItem(BaseModel):
    user_id: int
    name: str
    count: int


class DashboardProductivity(BaseModel):
    top_closers: List[AgentRankItem]
    top_commenters: List[AgentRankItem]
    most_active: List[AgentRankItem]


class BottleneckItem(BaseModel):
    name: str
    avg_hours: float
    ticket_count: int


class DashboardBottlenecks(BaseModel):
    by_team: List[BottleneckItem]
    by_category: List[BottleneckItem]
    by_hotel: List[BottleneckItem]


class VolumeItem(BaseModel):
    name: str
    count: int


class DashboardVolume(BaseModel):
    by_category: List[VolumeItem]
    by_subcategory: List[VolumeItem]
    by_hotel: List[VolumeItem]


class MonthlyPoint(BaseModel):
    month: str
    created: int
    closed: int


class DashboardHistory(BaseModel):
    monthly: List[MonthlyPoint]


# --------------------
# Dashboard SLA
# --------------------

class SLASummary(BaseModel):
    total_with_sla: int
    active_sla: int
    resolution_breached_open: int
    at_risk: int
    overall_compliance_pct: float
    avg_response_hours: Optional[float]

class SLATeamRow(BaseModel):
    team_name: str
    total: int
    compliant: int
    breached: int
    compliance_pct: float
    avg_response_hours: Optional[float]

class SLAPolicyRow(BaseModel):
    policy_name: str
    priority: str
    total: int
    compliant: int
    breached: int
    compliance_pct: float

class SLATicketItem(BaseModel):
    id: int
    title: str
    hotel_name: str
    team_name: Optional[str]
    policy_name: Optional[str]
    priority: str
    resolution_deadline: datetime
    hours_diff: float

class DashboardSLA(BaseModel):
    summary: SLASummary
    by_team: List[SLATeamRow]
    by_policy: List[SLAPolicyRow]
    at_risk_tickets: List[SLATicketItem]
    breached_open_tickets: List[SLATicketItem]


# ── TODO ─────────────────────────────────────────────────────────────────────

class TodoCreate(BaseModel):
    body: str

class TodoOut(BaseModel):
    id: int
    body: str
    done: bool
    done_at: Optional[datetime] = None
    created_at: datetime
    creator: UserBasic
    assignee: UserBasic

    class Config:
        from_attributes = True

class ScheduleVisitInput(BaseModel):
    scheduled_at: datetime
