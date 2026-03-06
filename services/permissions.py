TICKET_FIELD_UPDATE_PERMISSIONS = {
    "admin": {
        "status", "priority", "assigned_to",
        "category_id", "subcategory_id",
        "hotel_id", "progress",
        "title", "description"
    },
    "agent": {
        "status",
        "priority",
        "progress",
        "assigned_to",
        "category_id",
        "subcategory_id"
    },
    "client_manager": {"title", "description"},
    "client_receptionist": {"title", "description"},
}

def can_update_ticket_field(role: str, field_name: str) -> bool:
    allowed_fields = TICKET_FIELD_UPDATE_PERMISSIONS.get(role, set())
    return field_name in allowed_fields