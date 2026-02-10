ROLE_FIELD_PERMISSIONS = {
    "admin": {
        "status", "priority", "assigned_to",
        "category_id", "subcategory_id",
        "hotel_id", "progress",
        "title", "description"
    },
    "agent": {"status", "priority", "progress", "assigned_to"},
    "client_manager": {"title", "description"},
    "client_receptionist": {"title", "description"},
}

def validate_field_permission(role: str, field: str):
    allowed = ROLE_FIELD_PERMISSIONS.get(role, set())
    return field in allowed
    