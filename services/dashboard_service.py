from models import Ticket as TicketModel, User as UserModel, TicketLog as TicketLogModel
from models import TicketComment as CommentModel
from models import StatusEnum, ProgressEnum, PriorityEnum, LogActionEnum, RoleEnum
from datetime import datetime, timezone, timedelta

from sqlalchemy.sql import func
from sqlalchemy.orm import joinedload
from sqlalchemy import text


def dashboard_overview_service(
    current_user,
    db
):
    row = db.execute(text("""
        SELECT
          SUM(status = 'open')                                                   AS open_tickets,
          SUM(status = 'open' AND progress = 'in_progress')                     AS in_progress_tickets,
          SUM(status = 'open' AND progress = 'feedback')                         AS feedback_tickets,
          SUM(status = 'open' AND progress = 'awaiting_confirmation')            AS awaiting_confirmation_tickets,
          SUM(status = 'open' AND assigned_to IS NULL)                           AS unassigned_tickets,
          SUM(status = 'open' AND priority = 'high')                             AS high_priority_tickets,
          SUM(DATE(created_at) = CURDATE())                                      AS created_today_tickets,
          SUM(status = 'open' AND updated_at < NOW() - INTERVAL 48 HOUR)        AS stale_48h_tickets,
          SUM(status = 'closed' AND DATE(updated_at) = CURDATE())                AS closed_today_tickets,
          SUM(status = 'open' AND progress = 'scheduled_visit')                  AS scheduled_visit_tickets
        FROM tickets
    """)).fetchone()

    return {
        "open_tickets":                   int(row.open_tickets or 0),
        "in_progress_tickets":            int(row.in_progress_tickets or 0),
        "feedback_tickets":               int(row.feedback_tickets or 0),
        "awaiting_confirmation_tickets":  int(row.awaiting_confirmation_tickets or 0),
        "unassigned_tickets":             int(row.unassigned_tickets or 0),
        "stale_48h_tickets":              int(row.stale_48h_tickets or 0),
        "high_priority_tickets":          int(row.high_priority_tickets or 0),
        "created_today_tickets":          int(row.created_today_tickets or 0),
        "closed_today_tickets":           int(row.closed_today_tickets or 0),
        "scheduled_visit_tickets":        int(row.scheduled_visit_tickets or 0),
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
        GROUP BY s.name
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
    AT_RISK_HOURS = 8

    # ── Agregações globais via SQL ────────────────────────────────────
    summary_row = db.execute(text("""
        SELECT
          COUNT(*)                                                                          AS total_with_sla,
          SUM(ts.resolution_breached = 0 AND ts.resolution_met_at IS NULL
              AND t.status = 'open')                                                       AS active_sla,
          SUM(ts.resolution_breached = 1 AND t.status = 'open')                           AS resolution_breached_open,
          SUM(ts.resolution_breached = 1)                                                  AS resolved_breached,
          SUM(ts.resolution_met_at IS NOT NULL AND ts.resolution_breached = 0)            AS resolved_compliant,
          AVG(CASE WHEN ts.response_met_at IS NOT NULL
                   THEN TIMESTAMPDIFF(SECOND, ts.started_at, ts.response_met_at) / 3600.0
              END)                                                                          AS avg_response_hours
        FROM ticket_sla ts
        JOIN tickets t ON t.id = ts.ticket_id
        WHERE t.status != 'cancelled'
    """)).fetchone()

    total_resolved = int(summary_row.resolved_compliant or 0) + int(summary_row.resolved_breached or 0)
    overall_pct = round(int(summary_row.resolved_compliant or 0) / total_resolved * 100, 1) if total_resolved else 0.0

    # ── Agregação por equipe via SQL ──────────────────────────────────
    team_rows = db.execute(text("""
        SELECT
          COALESCE(tm.name, 'Sem equipe')                                                 AS team_name,
          COUNT(*)                                                                          AS total,
          SUM(ts.resolution_breached = 0 AND ts.resolution_met_at IS NOT NULL)            AS compliant,
          SUM(ts.resolution_breached = 1)                                                  AS breached,
          AVG(CASE WHEN ts.response_met_at IS NOT NULL
                   THEN TIMESTAMPDIFF(SECOND, ts.started_at, ts.response_met_at) / 3600.0
              END)                                                                          AS avg_response_hours
        FROM ticket_sla ts
        JOIN tickets t ON t.id = ts.ticket_id
        LEFT JOIN teams tm ON tm.id = t.assigned_team_id
        WHERE t.status != 'cancelled'
        GROUP BY tm.id, tm.name
        ORDER BY total DESC
    """)).fetchall()

    by_team = []
    for r in team_rows:
        c = int(r.compliant or 0)
        b = int(r.breached or 0)
        resolved = c + b
        pct = round(c / resolved * 100, 1) if resolved else 0.0
        by_team.append({
            "team_name": r.team_name,
            "total": int(r.total or 0),
            "compliant": c,
            "breached": b,
            "compliance_pct": pct,
            "avg_response_hours": round(float(r.avg_response_hours), 2) if r.avg_response_hours else None,
        })

    # ── Agregação por política via SQL ────────────────────────────────
    policy_rows = db.execute(text("""
        SELECT
          COALESCE(sp.name, 'Sem política')                                                AS policy_name,
          COALESCE(sp.priority, 'low')                                                     AS priority,
          COUNT(*)                                                                          AS total,
          SUM(ts.resolution_breached = 0 AND ts.resolution_met_at IS NOT NULL)            AS compliant,
          SUM(ts.resolution_breached = 1)                                                  AS breached
        FROM ticket_sla ts
        JOIN tickets t ON t.id = ts.ticket_id
        LEFT JOIN sla_policies sp ON sp.id = ts.policy_id
        WHERE t.status != 'cancelled'
        GROUP BY sp.id, sp.name, sp.priority
        ORDER BY total DESC
    """)).fetchall()

    by_policy = []
    for r in policy_rows:
        c = int(r.compliant or 0)
        b = int(r.breached or 0)
        resolved = c + b
        pct = round(c / resolved * 100, 1) if resolved else 0.0
        by_policy.append({
            "policy_name": r.policy_name,
            "priority": r.priority,
            "total": int(r.total or 0),
            "compliant": c,
            "breached": b,
            "compliance_pct": pct,
        })

    # ── Tickets em risco: candidatos via SQL, deadline efetivo em Python ─
    # Filtro conservador: deadline bruto dentro de (8h + margem pausa razoável).
    # Só carregamos candidatos (~dezenas), não todos os registros.
    AT_RISK_MARGIN_HOURS = AT_RISK_HOURS + 24  # margem para pausa acumulada
    candidate_rows = db.execute(text(f"""
        SELECT ts.ticket_id, ts.resolution_deadline, ts.total_paused_seconds, ts.paused_at,
               ts.resolution_breached, ts.resolution_met_at,
               t.title, t.priority, t.status,
               COALESCE(h.name, '') AS hotel_name,
               COALESCE(tm.name, 'Sem equipe') AS team_name,
               COALESCE(sp.name, 'Sem política') AS policy_name
        FROM ticket_sla ts
        JOIN tickets t ON t.id = ts.ticket_id
        LEFT JOIN hotels h ON h.id = t.hotel_id
        LEFT JOIN teams tm ON tm.id = t.assigned_team_id
        LEFT JOIN sla_policies sp ON sp.id = ts.policy_id
        WHERE t.status = 'open'
          AND ts.resolution_met_at IS NULL
          AND ts.resolution_deadline <= NOW() + INTERVAL {AT_RISK_MARGIN_HOURS} HOUR
        ORDER BY ts.resolution_deadline ASC
        LIMIT 100
    """)).fetchall()

    # Recalcula deadline efetivo (incluindo pausa ativa) em Python apenas para estes candidatos
    at_risk_list = []
    for r in candidate_rows:
        dl = r.resolution_deadline
        if dl.tzinfo is None:
            dl = dl.replace(tzinfo=timezone.utc)
        extra = r.total_paused_seconds or 0
        if r.paused_at:
            p = r.paused_at if r.paused_at.tzinfo else r.paused_at.replace(tzinfo=timezone.utc)
            extra += max(0, int((now - p).total_seconds()))
        eff_dl = dl + timedelta(seconds=extra)
        hours_diff = (eff_dl - now).total_seconds() / 3600

        if r.resolution_breached:
            continue  # breached_open é calculado separado
        if not (0 < hours_diff <= AT_RISK_HOURS):
            continue

        at_risk_list.append({
            "id": r.ticket_id,
            "title": r.title,
            "hotel_name": r.hotel_name,
            "team_name": r.team_name,
            "policy_name": r.policy_name,
            "priority": r.priority,
            "resolution_deadline": eff_dl,
            "hours_diff": hours_diff,
        })
    at_risk_list.sort(key=lambda x: x["hours_diff"])

    # ── Tickets com SLA violado e ainda abertos ───────────────────────
    breached_rows = db.execute(text("""
        SELECT ts.ticket_id, ts.resolution_deadline, ts.total_paused_seconds, ts.paused_at,
               t.title, t.priority,
               COALESCE(h.name, '') AS hotel_name,
               COALESCE(tm.name, 'Sem equipe') AS team_name,
               COALESCE(sp.name, 'Sem política') AS policy_name
        FROM ticket_sla ts
        JOIN tickets t ON t.id = ts.ticket_id
        LEFT JOIN hotels h ON h.id = t.hotel_id
        LEFT JOIN teams tm ON tm.id = t.assigned_team_id
        LEFT JOIN sla_policies sp ON sp.id = ts.policy_id
        WHERE t.status = 'open' AND ts.resolution_breached = 1
        ORDER BY ts.resolution_deadline ASC
        LIMIT 25
    """)).fetchall()

    breached_open_list = []
    for r in breached_rows:
        dl = r.resolution_deadline
        if dl.tzinfo is None:
            dl = dl.replace(tzinfo=timezone.utc)
        extra = r.total_paused_seconds or 0
        if r.paused_at:
            p = r.paused_at if r.paused_at.tzinfo else r.paused_at.replace(tzinfo=timezone.utc)
            extra += max(0, int((now - p).total_seconds()))
        eff_dl = dl + timedelta(seconds=extra)
        breached_open_list.append({
            "id": r.ticket_id,
            "title": r.title,
            "hotel_name": r.hotel_name,
            "team_name": r.team_name,
            "policy_name": r.policy_name,
            "priority": r.priority,
            "resolution_deadline": eff_dl,
            "hours_diff": (eff_dl - now).total_seconds() / 3600,
        })
    breached_open_list.sort(key=lambda x: x["hours_diff"])

    return {
        "summary": {
            "total_with_sla":           int(summary_row.total_with_sla or 0),
            "active_sla":               int(summary_row.active_sla or 0),
            "resolution_breached_open": int(summary_row.resolution_breached_open or 0),
            "at_risk":                  len(at_risk_list),
            "overall_compliance_pct":   overall_pct,
            "avg_response_hours":       round(float(summary_row.avg_response_hours), 2) if summary_row.avg_response_hours else None,
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