import re
from sqlalchemy.orm import Session
from models import Notification as NotificationModel, User as UserModel, UserHotel as UserHotelModel, UserTeam as UserTeamModel, RoleEnum


def create_notification(
    db: Session,
    user_id: int,
    type: str,
    title: str,
    body: str = None,
    ticket_id: int = None,
    mural_post_id: int = None,
    qualitor_ticket_id: int = None,
):
    notif = NotificationModel(
        user_id=user_id,
        type=type,
        title=title,
        body=body,
        ticket_id=ticket_id,
        mural_post_id=mural_post_id,
        qualitor_ticket_id=qualitor_ticket_id,
    )
    db.add(notif)


def notify_all_staff(
    db: Session,
    exclude_user_id: int,
    type: str,
    title: str,
    body: str = None,
    mural_post_id: int = None,
    ticket_id: int = None,
):
    """Notify all admin/agent users except the actor."""
    staff = (
        db.query(UserModel)
        .filter(
            UserModel.role.in_([RoleEnum.admin, RoleEnum.agent]),
            UserModel.id != exclude_user_id,
        )
        .all()
    )
    for u in staff:
        create_notification(db, u.id, type, title, body, ticket_id=ticket_id, mural_post_id=mural_post_id)


def notify_ticket_clients(
    db: Session,
    hotel_id: int,
    exclude_user_id: int,
    type: str,
    title: str,
    body: str = None,
    ticket_id: int = None,
):
    """Notify all client_manager/client_receptionist linked to the hotel, except the actor."""
    clients = (
        db.query(UserModel)
        .join(UserHotelModel, UserModel.id == UserHotelModel.user_id)
        .filter(
            UserHotelModel.hotel_id == hotel_id,
            UserModel.role.in_([RoleEnum.client_manager, RoleEnum.client_receptionist]),
            UserModel.id != exclude_user_id,
        )
        .all()
    )
    for u in clients:
        create_notification(db, u.id, type, title, body, ticket_id=ticket_id)


def notify_ticket_team(
    db: Session,
    team_id: int,
    exclude_user_id: int,
    type: str,
    title: str,
    body: str = None,
    ticket_id: int = None,
):
    """Notify all admins + agents who belong to the given team, except the actor."""
    admins = (
        db.query(UserModel)
        .filter(
            UserModel.role == RoleEnum.admin,
            UserModel.id != exclude_user_id,
        )
        .all()
    )
    agents = (
        db.query(UserModel)
        .join(UserTeamModel, UserModel.id == UserTeamModel.user_id)
        .filter(
            UserTeamModel.team_id == team_id,
            UserModel.role == RoleEnum.agent,
            UserModel.id != exclude_user_id,
        )
        .all()
    )
    seen = set()
    for u in admins + agents:
        if u.id not in seen:
            seen.add(u.id)
            create_notification(db, u.id, type, title, body, ticket_id=ticket_id)


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
