import re
from sqlalchemy.orm import Session
from models import Notification as NotificationModel, User as UserModel


def create_notification(
    db: Session,
    user_id: int,
    type: str,
    title: str,
    body: str = None,
    ticket_id: int = None,
):
    notif = NotificationModel(
        user_id=user_id,
        type=type,
        title=title,
        body=body,
        ticket_id=ticket_id,
    )
    db.add(notif)


def extract_mentioned_users(text: str, db: Session, exclude_user_id: int = None):
    """Parse @FirstName patterns from comment text and return matching users."""
    pattern = r'@(\w+)'
    matches = re.findall(pattern, text)
    if not matches:
        return []

    all_users = db.query(UserModel).all()
    mentioned = []
    seen_ids = set()

    for match in matches:
        match_lower = match.lower()
        for user in all_users:
            if user.id in seen_ids:
                continue
            if exclude_user_id and user.id == exclude_user_id:
                continue
            first_name = user.name.split()[0].lower() if user.name else ''
            if first_name == match_lower:
                mentioned.append(user)
                seen_ids.add(user.id)
                break

    return mentioned
