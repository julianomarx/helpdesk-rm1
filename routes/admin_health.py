import json
import os
import subprocess
from datetime import date, datetime

import httpx
from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy import desc
from sqlalchemy.orm import Session

from auth_utils import get_current_user
from config import BACKUP_REPORT_SECRET
from database import get_db
from models import SystemBackupReport, User as UserModel
from services.authorization import ensure_admin

router = APIRouter(prefix="/admin", tags=["admin"])

QUALITOR_API_URL = os.getenv("QUALITOR_API_URL", "http://localhost:8003")


def _service_status(name: str) -> str:
    try:
        r = subprocess.run(
            ["/usr/bin/systemctl", "is-active", name],
            capture_output=True, text=True, timeout=5,
        )
        return r.stdout.strip()  # "active" | "inactive" | "failed"
    except Exception:
        return "unknown"


@router.get("/health")
async def get_health(
    _: UserModel = Depends(ensure_admin),
    db: Session = Depends(get_db),
):
    services = {
        "qualitor_api":  _service_status("qualitor-api"),
        "qualitor_sync": _service_status("qualitor-sync"),
        "helpdesk_api":  "active",  # se chegou aqui, está ativo
    }

    qualitor_stats = {}
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            r = await client.get(f"{QUALITOR_API_URL}/admin/stats")
            if r.status_code == 200:
                qualitor_stats = r.json()
            else:
                qualitor_stats = {"error": f"HTTP {r.status_code}"}
    except Exception as e:
        qualitor_stats = {"error": str(e)}

    reports = (
        db.query(SystemBackupReport)
        .order_by(desc(SystemBackupReport.report_date), desc(SystemBackupReport.received_at))
        .limit(14)
        .all()
    )

    backups = [
        {
            "id":           r.id,
            "date":         r.report_date.isoformat() if r.report_date else None,
            "time":         r.report_time,
            "status":       r.status,
            "errors_count": r.errors_count,
            "total_size":   r.total_size,
            "disk_free":    r.disk_free,
            "report_lines": json.loads(r.report_lines) if r.report_lines else [],
            "received_at":  r.received_at.isoformat() if r.received_at else None,
        }
        for r in reports
    ]

    return {
        "services":      services,
        "qualitor":      qualitor_stats,
        "backups":       backups,
        "generated_at":  datetime.now().isoformat(),
    }


@router.post("/backup-report")
def receive_backup_report(
    payload: dict,
    x_backup_secret: str = Header(None),
    db: Session = Depends(get_db),
):
    if not BACKUP_REPORT_SECRET or x_backup_secret != BACKUP_REPORT_SECRET:
        raise HTTPException(status_code=401, detail="Unauthorized")

    try:
        report_date = date.fromisoformat(payload.get("report_date", date.today().isoformat()))
    except ValueError:
        report_date = date.today()

    report = SystemBackupReport(
        report_date=report_date,
        report_time=payload.get("report_time", ""),
        status=payload.get("status", "error"),
        errors_count=int(payload.get("errors_count", 0)),
        total_size=payload.get("total_size", ""),
        disk_free=payload.get("disk_free", ""),
        report_lines=json.dumps(payload.get("report_lines", []), ensure_ascii=False),
    )
    db.add(report)
    db.commit()
    return {"ok": True}
