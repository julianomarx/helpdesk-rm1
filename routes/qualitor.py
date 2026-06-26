import os
import httpx
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from typing import Optional

from auth_utils import get_current_user

router = APIRouter(prefix="/qualitor", tags=["qualitor"])

QUALITOR_API_URL = os.getenv("QUALITOR_API_URL", "http://localhost:8003")


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
async def qualitor_status(_=Depends(get_current_user)):
    return await _proxy_get("/qualitor/status")


@router.get("/tickets")
async def qualitor_tickets(
    situacao: Optional[str] = Query(None),
    equipe: Optional[str] = Query(None),
    _=Depends(get_current_user),
):
    params = {}
    if situacao:
        params["situacao"] = situacao
    if equipe:
        params["equipe"] = equipe
    return await _proxy_get("/qualitor/tickets", params)


@router.get("/tickets/{ticket_id}/history")
async def qualitor_ticket_history(ticket_id: int, _=Depends(get_current_user)):
    return await _proxy_get(f"/qualitor/tickets/{ticket_id}/history")


@router.get("/tickets/{ticket_id}")
async def qualitor_ticket_detail(ticket_id: int, _=Depends(get_current_user)):
    return await _proxy_get(f"/qualitor/tickets/{ticket_id}")


@router.post("/tickets/{ticket_id}/start")
async def qualitor_start_ticket(ticket_id: int, request: Request, user=Depends(get_current_user)):
    body = await request.json()
    body["tecnico"] = user.name  # usa o nome do usuário autenticado
    return await _proxy_post(f"/qualitor/tickets/{ticket_id}/start", body)


@router.post("/tickets/{ticket_id}/close")
async def qualitor_close_ticket(ticket_id: int, request: Request, user=Depends(get_current_user)):
    body = await request.json()
    body["tecnico"] = user.name
    return await _proxy_post(f"/qualitor/tickets/{ticket_id}/close", body)


@router.post("/tickets/{ticket_id}/refresh")
async def qualitor_refresh_ticket(ticket_id: int, _=Depends(get_current_user)):
    return await _proxy_post(f"/qualitor/tickets/{ticket_id}/refresh", {})


@router.post("/tickets/{ticket_id}/history")
async def qualitor_add_history(ticket_id: int, request: Request, _=Depends(get_current_user)):
    return await _proxy_post(f"/qualitor/tickets/{ticket_id}/history", await request.json())
