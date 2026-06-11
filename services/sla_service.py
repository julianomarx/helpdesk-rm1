from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from models import (
    Ticket as TicketModel,
    TicketSLA as TicketSLAModel,
    TicketLog as TicketLogModel,
    SubCategory as SubCategoryModel,
    SLAPolicy as SLAPolicyModel,
    LogActionEnum,
)


def _now() -> datetime:
    return datetime.now(timezone.utc)


def apply_sla_to_ticket(ticket: TicketModel, db: Session) -> TicketSLAModel | None:
    """
    Cria ou substitui o registro TicketSLA com base na política da subcategoria.
    Também atualiza a prioridade do ticket para refletir a política de SLA.
    Retorna None se a subcategoria não tiver política configurada.
    """
    if not ticket.subcategory_id:
        return None

    subcategory = (
        db.query(SubCategoryModel)
        .filter(SubCategoryModel.id == ticket.subcategory_id)
        .first()
    )
    if not subcategory or not subcategory.sla_policy_id:
        return None

    policy: SLAPolicyModel = subcategory.sla_policy

    # Remove registro anterior caso a subcategoria tenha mudado
    existing = db.query(TicketSLAModel).filter(TicketSLAModel.ticket_id == ticket.id).first()
    if existing:
        db.delete(existing)
        db.flush()

    # created_at pode ser None se o flush ainda não fez o server_default retornar
    started_at = ticket.created_at or _now()
    if started_at.tzinfo is None:
        started_at = started_at.replace(tzinfo=timezone.utc)

    response_deadline = started_at + timedelta(hours=policy.first_response_hours)
    resolution_deadline = started_at + timedelta(hours=policy.resolution_hours)

    sla_record = TicketSLAModel(
        ticket_id=ticket.id,
        policy_id=policy.id,
        first_response_hours=policy.first_response_hours,
        resolution_hours=policy.resolution_hours,
        started_at=started_at,
        response_deadline=response_deadline,
        resolution_deadline=resolution_deadline,
        total_paused_seconds=0,
        response_breached=False,
        resolution_breached=False,
    )
    db.add(sla_record)

    # SLA define a prioridade do ticket automaticamente
    ticket.priority = policy.priority

    log = TicketLogModel(
        ticket_id=ticket.id,
        user_id=None,
        action=LogActionEnum.sla_started.value,
        value=policy.name,
    )
    db.add(log)

    return sla_record


def _ensure_tz(dt: datetime) -> datetime:
    """Garante que o datetime tem tzinfo (MySQL devolve naive)."""
    if dt is not None and dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


def mark_response_met(ticket: TicketModel, db: Session) -> None:
    """Marca o prazo de primeira resposta como cumprido (ao iniciar o atendimento)."""
    sla = db.query(TicketSLAModel).filter(TicketSLAModel.ticket_id == ticket.id).first()
    if not sla or sla.response_met_at:
        return

    now = _now()
    sla.response_met_at = now

    # Verifica violação retroativa (normaliza timezone antes de comparar)
    deadline = _ensure_tz(sla.response_deadline)
    effective_deadline = deadline + timedelta(seconds=sla.total_paused_seconds)
    if now > effective_deadline:
        sla.response_breached = True

    log = TicketLogModel(
        ticket_id=ticket.id,
        user_id=None,
        action=LogActionEnum.sla_started.value,
        value="response_met",
    )
    db.add(log)


def pause_sla(ticket: TicketModel, db: Session) -> None:
    """Pausa o relógio SLA (quando progress muda para 'feedback')."""
    sla = db.query(TicketSLAModel).filter(TicketSLAModel.ticket_id == ticket.id).first()
    if not sla or sla.paused_at:
        return

    sla.paused_at = _now()

    log = TicketLogModel(
        ticket_id=ticket.id,
        user_id=None,
        action=LogActionEnum.sla_paused.value,
        value=None,
    )
    db.add(log)


def resume_sla(ticket: TicketModel, db: Session) -> None:
    """Retoma o relógio SLA (quando progress sai de 'feedback')."""
    sla = db.query(TicketSLAModel).filter(TicketSLAModel.ticket_id == ticket.id).first()
    if not sla or not sla.paused_at:
        return

    now = _now()
    paused_at = _ensure_tz(sla.paused_at)

    paused_seconds = int((now - paused_at).total_seconds())
    sla.total_paused_seconds += paused_seconds
    sla.paused_at = None

    log = TicketLogModel(
        ticket_id=ticket.id,
        user_id=None,
        action=LogActionEnum.sla_resumed.value,
        value=str(paused_seconds),
    )
    db.add(log)


def mark_resolution_met(ticket: TicketModel, db: Session) -> None:
    """Marca o prazo de resolução como cumprido (ao fechar o ticket)."""
    sla = db.query(TicketSLAModel).filter(TicketSLAModel.ticket_id == ticket.id).first()
    if not sla or sla.resolution_met_at:
        return

    now = _now()

    # Se ainda estava pausado, acumula o tempo antes de finalizar
    if sla.paused_at:
        paused_at = _ensure_tz(sla.paused_at)
        sla.total_paused_seconds += int((now - paused_at).total_seconds())
        sla.paused_at = None

    sla.resolution_met_at = now

    deadline = _ensure_tz(sla.resolution_deadline)
    effective_deadline = deadline + timedelta(seconds=sla.total_paused_seconds)
    if now > effective_deadline:
        sla.resolution_breached = True
        log_action = LogActionEnum.sla_breached.value
    else:
        log_action = LogActionEnum.sla_stopped.value

    log = TicketLogModel(
        ticket_id=ticket.id,
        user_id=None,
        action=log_action,
        value=None,
    )
    db.add(log)
