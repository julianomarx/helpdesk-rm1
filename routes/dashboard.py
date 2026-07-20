import os
import httpx
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import List

from models import User as UserModel
from schemas import (
    DashboardOverview, DashboardOperational, DashboardProductivity,
    DashboardBottlenecks, DashboardVolume, DashboardHistory, DashboardSLA,
)
from database import get_db
from auth_utils import get_current_user
from services.dashboard_service import (
    dashboard_overview_service,
    operational_dashboard_service,
    productivity_dashboard_service,
    bottlenecks_dashboard_service,
    volume_dashboard_service,
    history_dashboard_service,
    sla_dashboard_service,
)

QUALITOR_API_URL = os.getenv("QUALITOR_API_URL", "http://localhost:8003")

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/overview", response_model=DashboardOverview)
def get_dashboard_overview(
    current_user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    return dashboard_overview_service(current_user, db)


@router.get("/operational", response_model=DashboardOperational)
def get_operational(
    current_user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    return operational_dashboard_service(current_user, db)


@router.get("/productivity", response_model=DashboardProductivity)
def get_productivity(
    current_user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    return productivity_dashboard_service(current_user, db)


@router.get("/bottlenecks", response_model=DashboardBottlenecks)
def get_bottlenecks(
    current_user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    return bottlenecks_dashboard_service(current_user, db)


@router.get("/volume", response_model=DashboardVolume)
def get_volume(
    current_user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    return volume_dashboard_service(current_user, db)


@router.get("/history", response_model=DashboardHistory)
def get_history(
    current_user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    return history_dashboard_service(current_user, db)


@router.get("/sla", response_model=DashboardSLA)
def get_sla_dashboard(
    current_user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    return sla_dashboard_service(current_user, db)


@router.get("/bottlenecks/hotels")
def get_bottlenecks_hotels_paginated(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    current_user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    offset = (page - 1) * page_size
    rows = db.execute(text("""
        SELECT h.name, ROUND(AVG(TIMESTAMPDIFF(HOUR, tk.created_at, tk.updated_at)), 1) AS avg_hours,
               COUNT(tk.id) AS ticket_count
        FROM tickets tk
        JOIN hotels h ON tk.hotel_id = h.id
        WHERE tk.status = 'closed'
        GROUP BY h.id, h.name
        ORDER BY avg_hours DESC
        LIMIT :limit OFFSET :offset
    """), {"limit": page_size, "offset": offset}).fetchall()

    total = db.execute(text("""
        SELECT COUNT(DISTINCT tk.hotel_id) FROM tickets tk
        WHERE tk.status = 'closed' AND tk.hotel_id IS NOT NULL
    """)).scalar() or 0

    return {
        "items": [{"name": r.name, "avg_hours": float(r.avg_hours or 0), "ticket_count": r.ticket_count} for r in rows],
        "total": total,
        "page": page,
        "page_size": page_size,
        "pages": max(1, -(-total // page_size))
    }


# ─────────────────────────────────────────────────────────────────────────────
# DASHBOARD UNIFICADO (helpdesk + qualitor com toggle de fonte)
# ─────────────────────────────────────────────────────────────────────────────

async def _qualitor_stats(path: str, params: dict) -> dict:
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            r = await client.get(f"{QUALITOR_API_URL}/qualitor/stats/{path}", params=params)
            r.raise_for_status()
            return r.json()
    except Exception:
        return {}


def _hd_summary(period: str, db: Session) -> dict:
    days = {"7d": 7, "30d": 30, "90d": 90}.get(period, 30)
    rows = db.execute(text(f"""
        SELECT
          SUM(CASE WHEN status='open'   THEN 1 ELSE 0 END) AS abertos,
          SUM(CASE WHEN status='closed' AND updated_at >= NOW() - INTERVAL {days} DAY THEN 1 ELSE 0 END) AS fechados_periodo,
          SUM(CASE WHEN created_at >= NOW() - INTERVAL {days} DAY THEN 1 ELSE 0 END) AS abertos_periodo,
          AVG(CASE WHEN status='closed' AND updated_at >= NOW() - INTERVAL {days} DAY
              THEN TIMESTAMPDIFF(HOUR, created_at, updated_at) END) AS tempo_medio
        FROM tickets
    """)).fetchone()

    parados = db.execute(text(f"""
        SELECT COUNT(DISTINCT t.id) FROM tickets t
        WHERE t.status = 'open'
        AND NOT EXISTS (
          SELECT 1 FROM ticket_comments c
          WHERE c.ticket_id = t.id AND c.created_at >= NOW() - INTERVAL 5 DAY
        )
        AND t.updated_at < NOW() - INTERVAL 5 DAY
    """)).scalar() or 0

    return {
        "total_abertos":        rows.abertos or 0,
        "abertos_periodo":      rows.abertos_periodo or 0,
        "fechados_periodo":     rows.fechados_periodo or 0,
        "parados":              parados,
        "tempo_medio_resolucao_horas": round(float(rows.tempo_medio), 1) if rows.tempo_medio else None,
    }


def _hd_volume(period: str, db: Session) -> dict:
    days = {"7d": 7, "30d": 30, "90d": 90}.get(period, 30)
    abertos = db.execute(text(f"""
        SELECT DATE(created_at) AS dia, COUNT(*) AS total
        FROM tickets WHERE created_at >= NOW() - INTERVAL {days} DAY
        GROUP BY dia ORDER BY dia
    """)).fetchall()
    fechados = db.execute(text(f"""
        SELECT DATE(updated_at) AS dia, COUNT(*) AS total
        FROM tickets WHERE status='closed' AND updated_at >= NOW() - INTERVAL {days} DAY
        GROUP BY dia ORDER BY dia
    """)).fetchall()
    by_category = db.execute(text("""
        SELECT c.name, COUNT(tk.id) AS count
        FROM tickets tk JOIN categories c ON tk.category_id = c.id
        WHERE tk.status != 'cancelled'
        GROUP BY c.id, c.name ORDER BY count DESC LIMIT 15
    """)).fetchall()
    by_subcategory = db.execute(text("""
        SELECT s.name, COUNT(tk.id) AS count
        FROM tickets tk JOIN subcategories s ON tk.subcategory_id = s.id
        WHERE tk.status != 'cancelled'
        GROUP BY s.name ORDER BY count DESC LIMIT 15
    """)).fetchall()
    return {
        "abertos":        [{"dia": str(r.dia), "total": r.total} for r in abertos],
        "fechados":       [{"dia": str(r.dia), "total": r.total} for r in fechados],
        "by_category":    [{"name": r.name, "count": r.count} for r in by_category],
        "by_subcategory": [{"name": r.name, "count": r.count} for r in by_subcategory],
    }


def _hd_top_tech(period: str, db: Session) -> dict:
    days = {"7d": 7, "30d": 30, "90d": 90}.get(period, 30)
    fechamentos = db.execute(text(f"""
        SELECT u.name AS nome, COUNT(*) AS total
        FROM tickets t JOIN users u ON u.id = t.assigned_to
        WHERE t.status = 'closed' AND t.updated_at >= NOW() - INTERVAL {days} DAY
        AND t.assigned_to IS NOT NULL
        GROUP BY u.name ORDER BY total DESC LIMIT 10
    """)).fetchall()
    comentarios = db.execute(text(f"""
        SELECT u.name AS nome, COUNT(*) AS total
        FROM ticket_comments c JOIN users u ON u.id = c.user_id
        WHERE c.created_at >= NOW() - INTERVAL {days} DAY
        AND u.role NOT IN ('client_manager', 'client_receptionist')
        GROUP BY u.name ORDER BY total DESC LIMIT 10
    """)).fetchall()
    carga_atual = db.execute(text("""
        SELECT u.name AS nome, COUNT(*) AS total
        FROM tickets t JOIN users u ON u.id = t.assigned_to
        WHERE t.status = 'open' AND t.assigned_to IS NOT NULL
        GROUP BY u.name ORDER BY total DESC LIMIT 10
    """)).fetchall()
    return {
        "fechamentos": [{"nome": r.nome, "total": r.total} for r in fechamentos],
        "comentarios": [{"nome": r.nome, "total": r.total} for r in comentarios],
        "carga_atual": [{"nome": r.nome, "total": r.total} for r in carga_atual],
    }


def _hd_by_team(period: str, db: Session) -> dict:
    days = {"7d": 7, "30d": 30, "90d": 90}.get(period, 30)
    rows = db.execute(text(f"""
        SELECT tm.name AS equipe,
          SUM(CASE WHEN t.status='open' THEN 1 ELSE 0 END) AS abertos,
          SUM(CASE WHEN t.status='closed' AND t.updated_at >= NOW() - INTERVAL {days} DAY THEN 1 ELSE 0 END) AS fechados
        FROM tickets t JOIN teams tm ON tm.id = t.assigned_team_id
        WHERE tm.id IS NOT NULL GROUP BY tm.name ORDER BY abertos DESC
    """)).fetchall()
    return {"equipes": [{"equipe": r.equipe, "abertos": r.abertos, "fechados": r.fechados} for r in rows]}


def _hd_stalled(days_stalled: int, db: Session, limit: int = 25) -> dict:
    # Fetch limit+1 to detect if there are more without a separate COUNT query
    rows = db.execute(text(f"""
        SELECT t.id, t.title AS titulo, tm.name AS equipe, t.status AS situacao,
          u.name AS responsavel, t.created_at AS dtabertura,
          MAX(c.created_at) AS ultimo_acomp
        FROM tickets t
        LEFT JOIN users u ON u.id = t.assigned_to
        LEFT JOIN teams tm ON tm.id = t.assigned_team_id
        LEFT JOIN ticket_comments c ON c.ticket_id = t.id
        WHERE t.status = 'open'
        GROUP BY t.id
        HAVING ultimo_acomp IS NULL OR ultimo_acomp < NOW() - INTERVAL {days_stalled} DAY
        ORDER BY ultimo_acomp ASC LIMIT {limit + 1}
    """)).fetchall()
    has_more = len(rows) > limit
    rows = rows[:limit]
    return {"tickets": [
        {"id": r.id, "titulo": r.titulo, "equipe": r.equipe, "situacao": r.situacao,
         "responsavel": r.responsavel, "dtabertura": str(r.dtabertura) if r.dtabertura else None,
         "ultimo_acomp": str(r.ultimo_acomp) if r.ultimo_acomp else None}
        for r in rows
    ], "has_more": has_more}


def _merge_lists(key: str, *lists) -> list:
    merged: dict[str, int] = {}
    for lst in lists:
        for item in lst:
            name = item.get(key, "")
            merged[name] = merged.get(name, 0) + item.get("total", 0)
    return sorted([{key: k, "total": v} for k, v in merged.items()], key=lambda x: -x["total"])


def _merge_volume(*pairs) -> dict:
    from collections import defaultdict
    abertos: dict[str, int] = defaultdict(int)
    fechados: dict[str, int] = defaultdict(int)
    for ab, fe in pairs:
        for item in ab:
            abertos[item["dia"]] += item["total"]
        for item in fe:
            fechados[item["dia"]] += item["total"]
    return {
        "abertos":  sorted([{"dia": k, "total": v} for k, v in abertos.items()], key=lambda x: x["dia"]),
        "fechados": sorted([{"dia": k, "total": v} for k, v in fechados.items()], key=lambda x: x["dia"]),
    }


@router.get("/unified/summary")
async def unified_summary(
    source: str = Query("all"),
    period: str = Query("30d"),
    current_user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    hd, qt = {}, {}
    if source in ("helpdesk", "all"):
        hd = _hd_summary(period, db)
    if source in ("qualitor", "all"):
        qt = await _qualitor_stats("summary", {"period": period})

    if source == "helpdesk":
        return {**hd, "source": "helpdesk", "period": period}
    if source == "qualitor":
        return {**qt, "source": "qualitor"}

    return {
        "total_abertos":        (hd.get("total_abertos") or 0) + (qt.get("total_abertos") or 0),
        "abertos_periodo":      (hd.get("abertos_periodo") or 0) + (qt.get("abertos_periodo") or 0),
        "fechados_periodo":     (hd.get("fechados_periodo") or 0) + (qt.get("fechados_periodo") or 0),
        "parados":              (hd.get("parados") or 0) + (qt.get("parados") or 0),
        "tempo_medio_resolucao_horas": None,  # média de médias não é simples — exibir por fonte
        "hd_tempo_medio":       hd.get("tempo_medio_resolucao_horas"),
        "qt_tempo_medio":       qt.get("tempo_medio_resolucao_horas"),
        "source": "all",
        "period": period,
    }


@router.get("/unified/volume")
async def unified_volume(
    source: str = Query("all"),
    period: str = Query("30d"),
    current_user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    hd, qt = {"abertos": [], "fechados": [], "by_category": [], "by_subcategory": []}, {"abertos": [], "fechados": [], "by_category": [], "by_subcategory": []}
    if source in ("helpdesk", "all"):
        hd = _hd_volume(period, db)
    if source in ("qualitor", "all"):
        qt = await _qualitor_stats("volume", {"period": period})

    if source == "helpdesk":
        return {**hd, "source": "helpdesk", "period": period}
    if source == "qualitor":
        return {**qt, "source": "qualitor", "period": period}

    merged = _merge_volume(
        (hd.get("abertos", []), hd.get("fechados", [])),
        (qt.get("abertos", []), qt.get("fechados", [])),
    )
    by_category    = _merge_lists("name", hd.get("by_category",    []), qt.get("by_category",    []))
    by_subcategory = _merge_lists("name", hd.get("by_subcategory", []), qt.get("by_subcategory", []))
    return {
        **merged,
        "by_category":    by_category,
        "by_subcategory": by_subcategory,
        "by_hotel":       qt.get("by_hotel", []),
        "source": "all",
        "period": period,
    }


@router.get("/unified/top-technicians")
async def unified_top_technicians(
    source: str = Query("all"),
    period: str = Query("30d"),
    current_user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    hd, qt = {}, {}
    if source in ("helpdesk", "all"):
        hd = _hd_top_tech(period, db)
    if source in ("qualitor", "all"):
        qt = await _qualitor_stats("top-technicians", {"period": period})

    if source == "helpdesk":
        return {**hd, "source": "helpdesk", "period": period}
    if source == "qualitor":
        return {**qt, "source": "qualitor", "period": period}

    return {
        "fechamentos": _merge_lists("nome", hd.get("fechamentos", []), qt.get("fechamentos", []))[:10],
        "comentarios": _merge_lists("nome", hd.get("comentarios", []), qt.get("comentarios", []))[:10],
        "carga_atual": _merge_lists("nome", hd.get("carga_atual", []), qt.get("carga_atual", []))[:10],
        "source": "all",
        "period": period,
    }


@router.get("/unified/by-team")
async def unified_by_team(
    source: str = Query("all"),
    period: str = Query("30d"),
    current_user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    hd, qt = {}, {}
    if source in ("helpdesk", "all"):
        hd = _hd_by_team(period, db)
    if source in ("qualitor", "all"):
        qt = await _qualitor_stats("by-team", {"period": period})

    all_equipes: dict[str, dict] = {}
    for item in hd.get("equipes", []):
        all_equipes[item["equipe"]] = {"equipe": item["equipe"], "abertos": item["abertos"], "fechados": item["fechados"]}
    for item in qt.get("equipes", []):
        e = item["equipe"]
        if e in all_equipes:
            all_equipes[e]["abertos"]  += item["abertos"]
            all_equipes[e]["fechados"] += item["fechados"]
        else:
            all_equipes[e] = {"equipe": e, "abertos": item["abertos"], "fechados": item["fechados"]}

    return {
        "equipes": sorted(all_equipes.values(), key=lambda x: -x["abertos"]),
        "source": source,
        "period": period,
    }


@router.get("/unified/stalled")
async def unified_stalled(
    source: str = Query("all"),
    days: int = Query(5),
    limit: int = Query(25, ge=5, le=500),
    current_user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    hd_tickets, qt_tickets = [], []
    has_more = False
    if source in ("helpdesk", "all"):
        hd_result = _hd_stalled(days, db, limit=limit)
        hd_tickets = hd_result.get("tickets", [])
        has_more = has_more or hd_result.get("has_more", False)
        for t in hd_tickets:
            t["portal"] = "helpdesk"
    if source in ("qualitor", "all"):
        qt_data = await _qualitor_stats("stalled", {"days": days, "limit": limit})
        qt_tickets = qt_data.get("tickets", [])
        has_more = has_more or qt_data.get("has_more", False)
        for t in qt_tickets:
            t["portal"] = "qualitor"

    all_tickets = sorted(
        hd_tickets + qt_tickets,
        key=lambda x: (x.get("ultimo_acomp") or "0000"),
    )
    return {"tickets": all_tickets, "total": len(all_tickets), "has_more": has_more, "days": days, "source": source}


@router.get("/unified/sla")
async def unified_sla(
    source: str = Query("helpdesk"),
    period: str = Query("30d"),
    current_user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """SLA: helpdesk tem dados formais; qualitor usa estimativa por severidade."""
    days = {"7d": 7, "30d": 30, "90d": 90}.get(period, 30)
    result = {"source": source, "period": period, "portais": {}}

    if source in ("helpdesk", "all"):
        rows = db.execute(text(f"""
            SELECT
              SUM(CASE WHEN response_breached=0 AND resolution_breached=0 THEN 1 ELSE 0 END) AS ok,
              SUM(CASE WHEN response_breached=1 OR resolution_breached=1 THEN 1 ELSE 0 END) AS violado,
              COUNT(*) AS total
            FROM ticket_sla ts
            JOIN tickets t ON t.id = ts.ticket_id
            WHERE t.created_at >= NOW() - INTERVAL {days} DAY
        """)).fetchone()
        total = rows.total or 1
        result["portais"]["helpdesk"] = {
            "ok": rows.ok or 0,
            "violado": rows.violado or 0,
            "total": rows.total or 0,
            "ok_pct": round((rows.ok or 0) / total * 100, 1),
            "violado_pct": round((rows.violado or 0) / total * 100, 1),
            "formal": True,
        }

    if source in ("qualitor", "all"):
        qt = await _qualitor_stats("sla", {"period": period})
        result["portais"]["qualitor"] = {**qt, "formal": False, "estimado": True}

    return result


@router.get("/qualitor/stats/teams-breakdown")
async def qualitor_teams_breakdown(
    current_user: UserModel = Depends(get_current_user),
):
    """Proxy → qualitor API: resumo operacional por equipe (RM1 / RM1 SAP)."""
    return await _qualitor_stats("teams-breakdown", {})


@router.get("/qualitor/stats/sla-nativo")
async def qualitor_sla_nativo(
    current_user: UserModel = Depends(get_current_user),
):
    """Proxy → qualitor API: SLA nativo (campos reais do Qualitor)."""
    return await _qualitor_stats("sla-nativo", {})


@router.get("/qualitor/stats/bottlenecks")
async def qualitor_bottlenecks(
    period: str = Query("30d"),
    current_user: UserModel = Depends(get_current_user),
):
    """Proxy → qualitor API: gargalos (tempo médio por subcategoria e por hotel)."""
    return await _qualitor_stats("bottlenecks", {"period": period})


@router.get("/qualitor/stats/history")
async def qualitor_history(
    current_user: UserModel = Depends(get_current_user),
):
    """Proxy → qualitor API: histórico mensal de criados vs encerrados."""
    return await _qualitor_stats("history", {})