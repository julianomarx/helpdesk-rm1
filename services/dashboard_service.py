from models import Ticket as TicketModel, User as UserModel, TicketLog as TicketLogModel
from models import TicketComment as CommentModel, Hotel as HotelModel
from models import Category as CategoryModel, Team as TeamModel, SubCategory as SubCategoryModel
from models import TicketSLA as TicketSLAModel, SLAPolicy as SLAPolicyModel
from models import StatusEnum, ProgressEnum, PriorityEnum, LogActionEnum, RoleEnum
from datetime import datetime, timezone, timedelta
from collections import defaultdict

from sqlalchemy.sql import func
from sqlalchemy.orm import joinedload
from sqlalchemy import text


def dashboard_overview_service(
    current_user,
    db
):
    today = datetime.now(timezone.utc).date()
    cutoff = datetime.now(timezone.utc) - timedelta(hours=48)
    
    open_tickets = (
        db.query(TicketModel)
        .filter(TicketModel.status == StatusEnum.open)
        .count()
    )

    in_progress_tickets = (
        db.query(TicketModel)
        .filter(
            TicketModel.progress == ProgressEnum.in_progress,
            TicketModel.status == StatusEnum.open
        )
        .count()
    )

    feedback_tickets = (
        db.query(TicketModel)
        .filter(
            TicketModel.progress == ProgressEnum.feedback,
            TicketModel.status == StatusEnum.open
        )
        .count()
    )

    awaiting_confirmation_tickets = (
        db.query(TicketModel)
        .filter(
            TicketModel.progress == ProgressEnum.awaiting_confirmation,
            TicketModel.status == StatusEnum.open
        )
        .count()
    )

    unassigned_tickets = (
        db.query(TicketModel)
        .filter(
            TicketModel.assigned_to.is_(None),
            TicketModel.status == StatusEnum.open
        )
        .count()
    )

    high_priority_tickets = (
        db.query(TicketModel)
        .filter(
            TicketModel.priority == PriorityEnum.high,
            TicketModel.status == StatusEnum.open
        )
        .count()
    )

    created_today_tickets = (
        db.query(TicketModel)
        .filter(
            func.date(TicketModel.created_at) == today
        )
        .count()
    )

    stale_48h_tickets = (
        db.query(TicketModel)
        .filter(
            TicketModel.status == StatusEnum.open,
            TicketModel.updated_at < cutoff
        )
        .count()
    )

    closed_today_tickets = (
        db.query(TicketModel)
        .filter(
            TicketModel.status == StatusEnum.closed,
            func.date(TicketModel.updated_at) == today
        )
        .count()
    )

    scheduled_visit_tickets = (
        db.query(TicketModel)
        .filter(
            TicketModel.progress == ProgressEnum.scheduled_visit,
            TicketModel.status == StatusEnum.open
        )
        .count()
    )

    return {
        "open_tickets": open_tickets,
        "in_progress_tickets": in_progress_tickets,
        "feedback_tickets": feedback_tickets,
        "awaiting_confirmation_tickets": awaiting_confirmation_tickets,

        "unassigned_tickets": unassigned_tickets,
        "stale_48h_tickets": stale_48h_tickets,
        "high_priority_tickets": high_priority_tickets,
        "created_today_tickets": created_today_tickets,
        "closed_today_tickets": closed_today_tickets,
        "scheduled_visit_tickets": scheduled_visit_tickets,
    }


def _ticket_item(ticket):
    return {
        "id": ticket.id,
        "title": ticket.title,
        "hotel_name": ticket.hotel.name if ticket.hotel else "",
        "category_name": ticket.category.name if ticket.category else None,
        "priority": ticket.priority.value if hasattr(ticket.priority, "value") else ticket.priority,
        "assignee_name": ticket.assignee.name if ticket.assignee else None,
        "team_name": ticket.assigned_team.name if ticket.assigned_team else None,
        "created_at": ticket.created_at,
        "updated_at": ticket.updated_at,
        "progress": ticket.progress.value if hasattr(ticket.progress, "value") else ticket.progress,
    }


def _ticket_query(db):
    return (
        db.query(TicketModel)
        .options(
            joinedload(TicketModel.hotel),
            joinedload(TicketModel.category),
            joinedload(TicketModel.assignee),
            joinedload(TicketModel.assigned_team),
        )
    )


def operational_dashboard_service(current_user, db):
    LIMIT = 25
    cutoff_24h = datetime.now(timezone.utc) - timedelta(hours=24)

    stale = (
        _ticket_query(db)
        .filter(TicketModel.status == StatusEnum.open, TicketModel.updated_at < cutoff_24h)
        .order_by(TicketModel.updated_at.asc())
        .limit(LIMIT).all()
    )

    unassigned = (
        _ticket_query(db)
        .filter(TicketModel.status == StatusEnum.open, TicketModel.assigned_to.is_(None))
        .order_by(TicketModel.created_at.asc())
        .limit(LIMIT).all()
    )

    critical = (
        _ticket_query(db)
        .filter(TicketModel.status == StatusEnum.open, TicketModel.priority == PriorityEnum.high)
        .order_by(TicketModel.created_at.asc())
        .limit(LIMIT).all()
    )

    awaiting = (
        _ticket_query(db)
        .filter(
            TicketModel.status == StatusEnum.open,
            TicketModel.progress == ProgressEnum.awaiting_confirmation
        )
        .order_by(TicketModel.updated_at.asc())
        .limit(LIMIT).all()
    )

    feedback = (
        _ticket_query(db)
        .filter(
            TicketModel.status == StatusEnum.open,
            TicketModel.progress == ProgressEnum.feedback
        )
        .order_by(TicketModel.updated_at.asc())
        .limit(LIMIT).all()
    )

    return {
        "stale_tickets": [_ticket_item(t) for t in stale],
        "unassigned_tickets": [_ticket_item(t) for t in unassigned],
        "critical_tickets": [_ticket_item(t) for t in critical],
        "awaiting_confirmation_tickets": [_ticket_item(t) for t in awaiting],
        "feedback_tickets": [_ticket_item(t) for t in feedback],
    }


def productivity_dashboard_service(current_user, db):
    month_start = datetime.now(timezone.utc).replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    # Conta quem enviou o ticket para awaiting_confirmation (o agente que resolveu),
    # filtrando apenas tickets que foram de fato encerrados (status=closed).
    # Tickets retornados para a fila não pontuam.
    closers = (
        db.query(UserModel.id, UserModel.name, func.count(TicketLogModel.id).label("count"))
        .join(TicketLogModel, UserModel.id == TicketLogModel.user_id)
        .join(TicketModel, TicketModel.id == TicketLogModel.ticket_id)
        .filter(
            TicketLogModel.action == LogActionEnum.progress_changed.value,
            TicketLogModel.value == str(ProgressEnum.awaiting_confirmation),
            TicketLogModel.created_at >= month_start,
            UserModel.role.in_([RoleEnum.admin, RoleEnum.agent]),
            TicketModel.status == StatusEnum.closed,
        )
        .group_by(UserModel.id, UserModel.name)
        .order_by(func.count(TicketLogModel.id).desc())
        .limit(10).all()
    )

    commenters = (
        db.query(UserModel.id, UserModel.name, func.count(CommentModel.id).label("count"))
        .join(CommentModel, UserModel.id == CommentModel.user_id)
        .filter(
            CommentModel.created_at >= month_start,
            UserModel.role.in_([RoleEnum.admin, RoleEnum.agent]),
        )
        .group_by(UserModel.id, UserModel.name)
        .order_by(func.count(CommentModel.id).desc())
        .limit(10).all()
    )

    active = (
        db.query(UserModel.id, UserModel.name, func.count(TicketModel.id).label("count"))
        .join(TicketModel, UserModel.id == TicketModel.assigned_to)
        .filter(TicketModel.status == StatusEnum.open)
        .group_by(UserModel.id, UserModel.name)
        .order_by(func.count(TicketModel.id).desc())
        .limit(10).all()
    )

    return {
        "top_closers":   [{"user_id": r.id, "name": r.name, "count": r.count} for r in closers],
        "top_commenters":[{"user_id": r.id, "name": r.name, "count": r.count} for r in commenters],
        "most_active":   [{"user_id": r.id, "name": r.name, "count": r.count} for r in active],
    }


def bottlenecks_dashboard_service(current_user, db):
    by_team = db.execute(text("""
        SELECT t.name, ROUND(AVG(TIMESTAMPDIFF(HOUR, tk.created_at, tk.updated_at)), 1) AS avg_hours,
               COUNT(tk.id) AS ticket_count
        FROM tickets tk
        JOIN teams t ON tk.assigned_team_id = t.id
        WHERE tk.status = 'closed'
        GROUP BY t.id, t.name
        ORDER BY avg_hours DESC
        LIMIT 15
    """)).fetchall()

    by_category = db.execute(text("""
        SELECT c.name, ROUND(AVG(TIMESTAMPDIFF(HOUR, tk.created_at, tk.updated_at)), 1) AS avg_hours,
               COUNT(tk.id) AS ticket_count
        FROM tickets tk
        JOIN categories c ON tk.category_id = c.id
        WHERE tk.status = 'closed'
        GROUP BY c.id, c.name
        ORDER BY avg_hours DESC
        LIMIT 15
    """)).fetchall()

    by_hotel = db.execute(text("""
        SELECT h.name, ROUND(AVG(TIMESTAMPDIFF(HOUR, tk.created_at, tk.updated_at)), 1) AS avg_hours,
               COUNT(tk.id) AS ticket_count
        FROM tickets tk
        JOIN hotels h ON tk.hotel_id = h.id
        WHERE tk.status = 'closed'
        GROUP BY h.id, h.name
        ORDER BY avg_hours DESC
        LIMIT 10
    """)).fetchall()

    def row_to_dict(row):
        return {"name": row.name, "avg_hours": float(row.avg_hours or 0), "ticket_count": row.ticket_count}

    return {
        "by_team":     [row_to_dict(r) for r in by_team],
        "by_category": [row_to_dict(r) for r in by_category],
        "by_hotel":    [row_to_dict(r) for r in by_hotel],
    }


def volume_dashboard_service(current_user, db):
    by_category = db.execute(text("""
        SELECT c.name, COUNT(tk.id) AS count
        FROM tickets tk
        JOIN categories c ON tk.category_id = c.id
        WHERE tk.status != 'cancelled'
        GROUP BY c.id, c.name
        ORDER BY count DESC
        LIMIT 15
    """)).fetchall()

    by_subcategory = db.execute(text("""
        SELECT s.name, COUNT(tk.id) AS count
        FROM tickets tk
        JOIN subcategories s ON tk.subcategory_id = s.id
        WHERE tk.status != 'cancelled'
        GROUP BY s.id, s.name
        ORDER BY count DESC
        LIMIT 15
    """)).fetchall()

    by_hotel = db.execute(text("""
        SELECT h.name, COUNT(tk.id) AS count
        FROM tickets tk
        JOIN hotels h ON tk.hotel_id = h.id
        WHERE tk.status != 'cancelled'
        GROUP BY h.id, h.name
        ORDER BY count DESC
        LIMIT 10
    """)).fetchall()

    return {
        "by_category":    [{"name": r.name, "count": r.count} for r in by_category],
        "by_subcategory": [{"name": r.name, "count": r.count} for r in by_subcategory],
        "by_hotel":       [{"name": r.name, "count": r.count} for r in by_hotel],
    }


def sla_dashboard_service(current_user, db):
    now = datetime.now(timezone.utc)
    AT_RISK_HOURS = 8  # considera "em risco" quem vence nas próximas 8h

    records = (
        db.query(TicketSLAModel)
        .join(TicketModel, TicketSLAModel.ticket_id == TicketModel.id)
        .options(
            joinedload(TicketSLAModel.ticket).joinedload(TicketModel.hotel),
            joinedload(TicketSLAModel.ticket).joinedload(TicketModel.assigned_team),
            joinedload(TicketSLAModel.policy),
        )
        .filter(TicketModel.status != StatusEnum.cancelled)
        .all()
    )

    def eff_deadline(r):
        dl = r.resolution_deadline
        if dl.tzinfo is None:
            dl = dl.replace(tzinfo=timezone.utc)
        extra = r.total_paused_seconds
        if r.paused_at:
            p = r.paused_at if r.paused_at.tzinfo else r.paused_at.replace(tzinfo=timezone.utc)
            extra += max(0, int((now - p).total_seconds()))
        return dl + timedelta(seconds=extra)

    def eff_response_deadline(r):
        dl = r.response_deadline
        if dl.tzinfo is None:
            dl = dl.replace(tzinfo=timezone.utc)
        extra = r.total_paused_seconds
        if r.paused_at:
            p = r.paused_at if r.paused_at.tzinfo else r.paused_at.replace(tzinfo=timezone.utc)
            extra += max(0, int((now - p).total_seconds()))
        return dl + timedelta(seconds=extra)

    # ── Contadores globais ────────────────────────────────────────────
    total_with_sla = len(records)
    active_sla = 0
    at_risk = 0
    resolution_breached_open = 0
    resolved_compliant = 0
    resolved_breached = 0
    response_hours_list = []

    # ── Por equipe ────────────────────────────────────────────────────
    teams: dict[str, dict] = defaultdict(lambda: {"total": 0, "compliant": 0, "breached": 0, "response_hours": []})

    # ── Por política ──────────────────────────────────────────────────
    policies: dict[str, dict] = defaultdict(lambda: {"priority": "", "total": 0, "compliant": 0, "breached": 0})

    # ── Listas detalhadas ─────────────────────────────────────────────
    at_risk_list = []
    breached_open_list = []

    for r in records:
        ticket = r.ticket
        team_name = ticket.assigned_team.name if ticket.assigned_team else "Sem equipe"
        policy_name = r.policy.name if r.policy else "Sem política"
        policy_priority = (r.policy.priority.value if hasattr(r.policy.priority, "value") else r.policy.priority) if r.policy else "low"
        hotel_name = ticket.hotel.name if ticket.hotel else ""
        priority_val = ticket.priority.value if hasattr(ticket.priority, "value") else ticket.priority

        eff_dl = eff_deadline(r)
        hours_diff = (eff_dl - now).total_seconds() / 3600

        # Primeira resposta
        if r.response_met_at:
            resp_met = r.response_met_at if r.response_met_at.tzinfo else r.response_met_at.replace(tzinfo=timezone.utc)
            started = r.started_at if r.started_at.tzinfo else r.started_at.replace(tzinfo=timezone.utc)
            response_h = (resp_met - started).total_seconds() / 3600
            response_hours_list.append(response_h)
            teams[team_name]["response_hours"].append(response_h)

        # Classificação de compliance
        is_resolved = r.resolution_met_at is not None
        is_open = ticket.status == StatusEnum.open or ticket.status == StatusEnum.open.value

        if r.resolution_breached:
            resolved_breached += 1
            teams[team_name]["breached"] += 1
            policies[policy_name]["breached"] += 1
            if is_open:
                resolution_breached_open += 1
                breached_open_list.append({
                    "id": ticket.id,
                    "title": ticket.title,
                    "hotel_name": hotel_name,
                    "team_name": team_name,
                    "policy_name": policy_name,
                    "priority": priority_val,
                    "resolution_deadline": eff_dl,
                    "hours_diff": hours_diff,
                })
        elif is_resolved:
            resolved_compliant += 1
            teams[team_name]["compliant"] += 1
            policies[policy_name]["compliant"] += 1
        else:
            # Ainda ativo
            active_sla += 1
            if 0 < hours_diff <= AT_RISK_HOURS:
                at_risk += 1
                at_risk_list.append({
                    "id": ticket.id,
                    "title": ticket.title,
                    "hotel_name": hotel_name,
                    "team_name": team_name,
                    "policy_name": policy_name,
                    "priority": priority_val,
                    "resolution_deadline": eff_dl,
                    "hours_diff": hours_diff,
                })

        teams[team_name]["total"] += 1
        policies[policy_name]["total"] += 1
        if r.policy:
            policies[policy_name]["priority"] = policy_priority

    total_resolved = resolved_compliant + resolved_breached
    overall_pct = round((resolved_compliant / total_resolved * 100), 1) if total_resolved else 0.0
    avg_response = round(sum(response_hours_list) / len(response_hours_list), 2) if response_hours_list else None

    by_team = []
    for name, d in sorted(teams.items(), key=lambda x: -x[1]["total"]):
        t = d["total"]
        c = d["compliant"]
        b = d["breached"]
        resolved = c + b
        pct = round(c / resolved * 100, 1) if resolved else 0.0
        avg_r = round(sum(d["response_hours"]) / len(d["response_hours"]), 2) if d["response_hours"] else None
        by_team.append({"team_name": name, "total": t, "compliant": c, "breached": b, "compliance_pct": pct, "avg_response_hours": avg_r})

    by_policy = []
    for name, d in sorted(policies.items(), key=lambda x: -x[1]["total"]):
        t = d["total"]
        c = d["compliant"]
        b = d["breached"]
        resolved = c + b
        pct = round(c / resolved * 100, 1) if resolved else 0.0
        by_policy.append({"policy_name": name, "priority": d["priority"], "total": t, "compliant": c, "breached": b, "compliance_pct": pct})

    at_risk_list.sort(key=lambda x: x["hours_diff"])
    breached_open_list.sort(key=lambda x: x["hours_diff"])

    return {
        "summary": {
            "total_with_sla": total_with_sla,
            "active_sla": active_sla,
            "resolution_breached_open": resolution_breached_open,
            "at_risk": at_risk,
            "overall_compliance_pct": overall_pct,
            "avg_response_hours": avg_response,
        },
        "by_team": by_team,
        "by_policy": by_policy,
        "at_risk_tickets": at_risk_list[:25],
        "breached_open_tickets": breached_open_list[:25],
    }


def history_dashboard_service(current_user, db):
    created = db.execute(text("""
        SELECT DATE_FORMAT(created_at, '%Y-%m') AS month, COUNT(*) AS cnt
        FROM tickets
        WHERE created_at >= DATE_SUB(NOW(), INTERVAL 12 MONTH)
        GROUP BY month
        ORDER BY month
    """)).fetchall()

    closed = db.execute(text("""
        SELECT DATE_FORMAT(tl.created_at, '%Y-%m') AS month, COUNT(*) AS cnt
        FROM ticket_logs tl
        WHERE tl.action = 'ticket_closed'
          AND tl.created_at >= DATE_SUB(NOW(), INTERVAL 12 MONTH)
        GROUP BY month
        ORDER BY month
    """)).fetchall()

    created_map = {r.month: r.cnt for r in created}
    closed_map  = {r.month: r.cnt for r in closed}
    all_months  = sorted(set(list(created_map.keys()) + list(closed_map.keys())))

    return {
        "monthly": [
            {"month": m, "created": created_map.get(m, 0), "closed": closed_map.get(m, 0)}
            for m in all_months
        ]
    }