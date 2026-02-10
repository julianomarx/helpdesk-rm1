from enum import Enum


class RoleEnum(str, Enum):
    admin = "admin"
    agent = "agent"
    client_manager = "client_manager"
    client_receptionist = "client_receptionist"


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


class PriorityEnum(str, Enum):
    low = "low"
    medium = "medium"
    high = "high"


class LogActionEnum(str, Enum):
    created = "created"
    ticket_closed = "ticket_closed"
    ticket_reopened = "ticket_reopened"
    ticket_deleted = "ticket_deleted"

    status_changed = "status_changed"
    assigned_changed = "assigned_changed"
    priority_changed = "priority_changed"
    team_changed = "team_changed"
    category_changed = "category_changed"
    subcategory_changed = "subcategory_changed"

    comment_added = "comment_added"
    comment_updated = "comment_updated"
    comment_deleted = "comment_deleted"

    agent_joined = "agent_joined"
    agent_left = "agent_left"

    time_started = "time_started"
    time_paused = "time_paused"
    time_resumed = "time_resumed"
    time_stopped = "time_stopped"

    sla_started = "sla_started"
    sla_paused = "sla_paused"
    sla_resumed = "sla_resumed"
    sla_breached = "sla_breached"
    sla_stopped = "sla_stopped"
