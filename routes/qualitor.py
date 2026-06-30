import os
import httpx
from fastapi import APIRouter, Depends, HTTPException, Query, Request, UploadFile, File
from fastapi.responses import Response
from typing import Optional
from sqlalchemy.orm import Session

from auth_utils import get_current_user, QUALITOR_TEAM_NAMES
from database import get_db
from models import User as UserModel, UserTeam as UserTeamModel, Team as TeamModel
from schemas import RoleEnum
from services.notification_service import create_notification, extract_mentioned_users

router = APIRouter(prefix="/qualitor", tags=["qualitor"])

QUALITOR_API_URL = os.getenv("QUALITOR_API_URL", "http://localhost:8003")


def ensure_qualitor_access(
    current_user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> UserModel:
    """Admin sempre tem acesso. Agente precisa estar em RM1 ou RM1 SAP."""
    if current_user.role == RoleEnum.admin:
        return current_user
    in_qualitor_team = (
        db.query(UserTeamModel.team_id)
        .join(TeamModel, TeamModel.id == UserTeamModel.team_id)
        .filter(
            UserTeamModel.user_id == current_user.id,
            TeamModel.name.in_(QUALITOR_TEAM_NAMES),
        )
        .first()
    )
    if not in_qualitor_team:
        raise HTTPException(status_code=403, detail="Acesso restrito a membros das equipes RM1 ou RM1 SAP")
    return current_user


async def _proxy_get(path: str, params: dict = None):
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            r = await client.get(f"{QUALITOR_API_URL}{path}", params=params)
            r.raise_for_status()
            return r.json()
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=e.response.status_code, detail="Erro na API Qualitor")
    except httpx.RequestError:
        raise HTTPException(status_code=503, detail="API Qualitor indisponível")


async def _proxy_post(path: str, body: dict):
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            r = await client.post(f"{QUALITOR_API_URL}{path}", json=body)
            r.raise_for_status()
            return r.json()
    except httpx.HTTPStatusError as e:
        detail = "Erro na API Qualitor"
        try:
            detail = e.response.json().get("detail", detail)
        except Exception:
            pass
        raise HTTPException(status_code=e.response.status_code, detail=detail)
    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="Qualitor demorou demais para responder. Tente novamente.")
    except httpx.RequestError:
        raise HTTPException(status_code=503, detail="API Qualitor indisponível")


@router.get("/status")
async def qualitor_status(
    equipe: Optional[str] = Query(None),
    situacao: Optional[str] = Query(None),
    ativas_only: bool = Query(False),
    responsavel_interno_id: Optional[int] = Query(None),
    _=Depends(ensure_qualitor_access),
):
    params = {}
    if equipe:                   params["equipe"] = equipe
    if situacao:                 params["situacao"] = situacao
    if ativas_only:              params["ativas_only"] = True
    if responsavel_interno_id:   params["responsavel_interno_id"] = responsavel_interno_id
    return await _proxy_get("/qualitor/status", params)


@router.get("/tickets")
async def qualitor_tickets(
    situacao: Optional[str] = Query(None),
    equipe: Optional[str] = Query(None),
    responsavel_interno_id: Optional[int] = Query(None),
    ativas_only: bool = Query(False),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    current_user: UserModel = Depends(ensure_qualitor_access),
    db: Session = Depends(get_db),
):
    params: dict = {"page": page, "page_size": page_size}
    if situacao:
        params["situacao"] = situacao
    if ativas_only:
        params["ativas_only"] = True
    if responsavel_interno_id:
        params["responsavel_interno_id"] = responsavel_interno_id

    if current_user.role == RoleEnum.admin:
        # Admin sees everything — pass equipe as-is
        if equipe:
            params["equipe"] = equipe
    else:
        # Resolve which Qualitor teams this user is allowed to see
        allowed_rows = (
            db.query(TeamModel.name)
            .join(UserTeamModel, UserTeamModel.team_id == TeamModel.id)
            .filter(
                UserTeamModel.user_id == current_user.id,
                TeamModel.name.in_(QUALITOR_TEAM_NAMES),
            )
            .all()
        )
        allowed_teams = {row.name for row in allowed_rows}

        if len(allowed_teams) == 1:
            # Single team — always force it regardless of frontend param
            params["equipe"] = next(iter(allowed_teams))
        else:
            # Multiple teams — allow frontend to filter within allowed set
            if equipe and equipe in allowed_teams:
                params["equipe"] = equipe
            # else: no equipe restriction → backend returns all (RM1 + RM1 SAP)

    return await _proxy_get("/qualitor/tickets", params)


@router.post("/tickets/{ticket_id}/force-import")
async def qualitor_force_import(ticket_id: int, user=Depends(ensure_qualitor_access)):
    """Força importação de um ticket que não está no banco local (ex: encerrado antes do primeiro sync)."""
    return await _proxy_post(f"/qualitor/tickets/{ticket_id}/force-import", {})


@router.get("/tickets/{ticket_id}/history")
async def qualitor_ticket_history(ticket_id: int, _=Depends(ensure_qualitor_access)):
    return await _proxy_get(f"/qualitor/tickets/{ticket_id}/history")


@router.get("/tickets/{ticket_id}")
async def qualitor_ticket_detail(ticket_id: int, _=Depends(ensure_qualitor_access)):
    return await _proxy_get(f"/qualitor/tickets/{ticket_id}")


@router.post("/tickets/{ticket_id}/start")
async def qualitor_start_ticket(ticket_id: int, request: Request, user=Depends(ensure_qualitor_access)):
    body = await request.json()
    body["tecnico"] = user.name
    body.setdefault("responsavel_interno_id", user.id)
    body.setdefault("responsavel_interno_nome", user.name)
    return await _proxy_post(f"/qualitor/tickets/{ticket_id}/start", body)


@router.post("/tickets/{ticket_id}/close")
async def qualitor_close_ticket(ticket_id: int, request: Request, user=Depends(ensure_qualitor_access)):
    body = await request.json()
    body["tecnico"] = user.name
    body.setdefault("interno_user_id", user.id)
    body.setdefault("interno_user_nome", user.name)
    return await _proxy_post(f"/qualitor/tickets/{ticket_id}/close", body)


@router.post("/tickets/{ticket_id}/refresh")
async def qualitor_refresh_ticket(
    ticket_id: int,
    _: UserModel = Depends(ensure_qualitor_access),
    db: Session = Depends(get_db),
):
    data = await _proxy_post(f"/qualitor/tickets/{ticket_id}/refresh", {})

    # Notifica o responsável interno quando o cliente confirma o encerramento
    if data.get("confirmed_closed") and data.get("responsavel_interno_id"):
        create_notification(
            db,
            user_id=data["responsavel_interno_id"],
            type="ticket_closed",
            title=f"Chamado Qualitor #{ticket_id} encerrado pelo cliente",
            body=f"O cliente confirmou o encerramento do chamado #{ticket_id}.",
            qualitor_ticket_id=ticket_id,
        )
        db.commit()

    return data


@router.get("/teams")
async def qualitor_teams(_=Depends(ensure_qualitor_access)):
    return await _proxy_get("/qualitor/teams")


@router.post("/tickets/{ticket_id}/transfer")
async def qualitor_transfer_ticket(ticket_id: int, request: Request, user=Depends(ensure_qualitor_access)):
    body = await request.json()
    body["tecnico"] = user.name
    return await _proxy_post(f"/qualitor/tickets/{ticket_id}/transfer", body)


@router.post("/tickets/{ticket_id}/history")
async def qualitor_add_history(
    ticket_id: int,
    request: Request,
    user: UserModel = Depends(ensure_qualitor_access),
    db: Session = Depends(get_db),
):
    body = await request.json()
    body.setdefault("interno_user_id", user.id)
    body.setdefault("interno_user_nome", user.name)

    result = await _proxy_post(f"/qualitor/tickets/{ticket_id}/history", body)

    descricao = body.get("descricao", "")
    if descricao:
        first_name = user.name.split()[0] if user.name else user.name
        mentioned = extract_mentioned_users(descricao, db, exclude_user_id=user.id)
        for u in mentioned:
            create_notification(
                db,
                user_id=u.id,
                type="mention",
                title=f"@{first_name} mencionou você em um chamado Qualitor",
                body=f"Chamado #{ticket_id}: {descricao[:120]}",
                qualitor_ticket_id=ticket_id,
            )
        if mentioned:
            db.commit()

    return result


@router.post("/tickets/{ticket_id}/assign-interno")
async def qualitor_assign_interno(
    ticket_id: int,
    request: Request,
    user: UserModel = Depends(ensure_qualitor_access),
    db: Session = Depends(get_db),
):
    body = await request.json()
    body["user_id"]   = body.get("user_id") or user.id
    body["user_nome"] = body.get("user_nome") or user.name

    result = await _proxy_post(f"/qualitor/tickets/{ticket_id}/assign-interno", body)

    assigned_id = body["user_id"]
    if assigned_id != user.id:
        create_notification(
            db,
            user_id=assigned_id,
            type="ticket_assigned",
            title=f"Chamado Qualitor #{ticket_id} atribuído a você",
            body=f"Atribuído por {user.name}",
            qualitor_ticket_id=ticket_id,
        )
        db.commit()

    return result


@router.post("/tickets/{ticket_id}/schedule-visit")
async def qualitor_schedule_visit(
    ticket_id: int,
    request: Request,
    user: UserModel = Depends(ensure_qualitor_access),
):
    body = await request.json()
    body.setdefault("interno_user_id", user.id)
    body.setdefault("interno_user_nome", user.name)
    return await _proxy_post(f"/qualitor/tickets/{ticket_id}/schedule-visit", body)


@router.get("/reports/activity")
async def qualitor_reports_activity(
    interno_user_id: int = Query(...),
    start_date: str = Query(...),
    end_date: str = Query(...),
    current_user: UserModel = Depends(ensure_qualitor_access),
    db: Session = Depends(get_db),
):
    params = {
        "interno_user_id": interno_user_id,
        "start_date": start_date,
        "end_date": end_date,
    }
    data = await _proxy_get("/qualitor/reports/activity", params)

    # Enriquece o campo agent com name/email/role do DB do helpdesk
    agent_user = db.query(UserModel).filter(UserModel.id == interno_user_id).first()
    if agent_user and isinstance(data, dict) and "agent" in data:
        data["agent"]["name"]  = agent_user.name
        data["agent"]["email"] = agent_user.email
        data["agent"]["role"]  = agent_user.role

    return data


@router.get("/tickets/{ticket_id}/attachments")
async def qualitor_list_attachments(ticket_id: int, _=Depends(get_current_user)):
    return await _proxy_get(f"/qualitor/tickets/{ticket_id}/attachments")


@router.get("/tickets/{ticket_id}/attachments/{nrsequencia}/download")
async def qualitor_download_attachment(
    ticket_id: int,
    nrsequencia: int,
    nmanexo: str = Query(...),
    cdclassificacao: str = Query(""),
    _=Depends(get_current_user),
):
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            r = await client.get(
                f"{QUALITOR_API_URL}/qualitor/tickets/{ticket_id}/attachments/{nrsequencia}/download",
                params={"nmanexo": nmanexo, "cdclassificacao": cdclassificacao},
            )
            r.raise_for_status()
            return Response(
                content=r.content,
                media_type=r.headers.get("content-type", "application/octet-stream"),
                headers={"Content-Disposition": r.headers.get("content-disposition", "")},
            )
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=e.response.status_code, detail="Erro ao baixar anexo")
    except httpx.RequestError:
        raise HTTPException(status_code=503, detail="API Qualitor indisponível")


@router.post("/tickets/{ticket_id}/attachments")
async def qualitor_upload_attachment(
    ticket_id: int,
    file: UploadFile = File(...),
    _=Depends(get_current_user),
):
    content = await file.read()
    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            r = await client.post(
                f"{QUALITOR_API_URL}/qualitor/tickets/{ticket_id}/attachments",
                files={"file": (file.filename, content, file.content_type or "application/octet-stream")},
            )
            r.raise_for_status()
            return r.json()
    except httpx.HTTPStatusError as e:
        detail = "Erro ao fazer upload"
        try:
            detail = e.response.json().get("detail", detail)
        except Exception:
            pass
        raise HTTPException(status_code=e.response.status_code, detail=detail)
    except httpx.RequestError:
        raise HTTPException(status_code=503, detail="API Qualitor indisponível")
