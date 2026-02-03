from models import LogActionEnum

FIELD_TO_ACTION = {
    "status": LogActionEnum.status_changed,
    "priority": LogActionEnum.priority_changed,
    "assigned_to": LogActionEnum.assigned_changed,
    "assigned_team_id": LogActionEnum.team_changed,
    "category_id": LogActionEnum.category_changed,
    "subcategory_id": LogActionEnum.subcategory_changed,
}