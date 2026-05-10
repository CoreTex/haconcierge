from fastapi import APIRouter, Depends, Request, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import Optional
from database.db import get_db
from config import AppConfig

router = APIRouter(prefix="/api/settings", tags=["settings"])


class AISettings(BaseModel):
    ai_base_url: str
    ai_model: str
    ai_timeout: int = 30
    ai_temperature: float = 0.1


class O365Settings(BaseModel):
    o365_enabled: bool
    o365_tenant_id: str
    o365_client_id: str
    o365_client_secret: str
    o365_group_email: str
    o365_planner_plan_id: str


class NotificationSettings(BaseModel):
    wa_proactive_notify: bool


@router.get("")
def get_settings(db: Session = Depends(get_db)):
    cfg = AppConfig(db)
    all_settings = cfg.get_all()
    # Never expose secrets in plain text – mask them
    if all_settings.get("o365_client_secret"):
        all_settings["o365_client_secret"] = "***"
    return all_settings


@router.put("/ai")
async def update_ai_settings(body: AISettings, request: Request, db: Session = Depends(get_db)):
    cfg = AppConfig(db)
    cfg.set_many({
        "ai_base_url": body.ai_base_url,
        "ai_model": body.ai_model,
        "ai_timeout": str(body.ai_timeout),
        "ai_temperature": str(body.ai_temperature),
    })
    # Reinitialize AI client in app state
    from ai.client import AIClient
    request.app.state.ai_client = AIClient(
        base_url=body.ai_base_url,
        model=body.ai_model,
        timeout=body.ai_timeout,
        temperature=body.ai_temperature,
    )
    return {"success": True}


@router.get("/ai/models")
async def list_available_models(request: Request):
    ai_client = request.app.state.ai_client
    if not ai_client:
        return {"models": []}
    models = await ai_client.list_models()
    return {"models": models}


@router.get("/ai/health")
async def ai_health(request: Request):
    ai_client = request.app.state.ai_client
    if not ai_client:
        return {"ok": False, "reason": "No AI endpoint configured"}
    ok = await ai_client.health_check()
    return {"ok": ok}


@router.put("/o365")
async def update_o365_settings(body: O365Settings, request: Request, db: Session = Depends(get_db)):
    cfg = AppConfig(db)
    update = body.model_dump()
    update["o365_enabled"] = "true" if body.o365_enabled else "false"
    # Don't overwrite secret if masked
    if update.get("o365_client_secret") == "***":
        del update["o365_client_secret"]
    cfg.set_many({k: str(v) for k, v in update.items()})
    # Reinitialize O365 clients
    await _reinit_o365(request, cfg)
    return {"success": True}


@router.put("/notifications")
def update_notification_settings(body: NotificationSettings, db: Session = Depends(get_db)):
    cfg = AppConfig(db)
    cfg.set("wa_proactive_notify", "true" if body.wa_proactive_notify else "false")
    return {"success": True}


async def _reinit_o365(request: Request, cfg: AppConfig) -> None:
    if cfg.get("o365_enabled") != "true":
        request.app.state.o365_cal = None
        request.app.state.o365_tasks = None
        return
    from o365.auth import O365Auth
    from o365.calendar import O365CalendarClient
    from o365.tasks import O365TasksClient
    auth = O365Auth(
        tenant_id=cfg.get("o365_tenant_id") or "",
        client_id=cfg.get("o365_client_id") or "",
        client_secret=cfg.get("o365_client_secret") or "",
    )
    request.app.state.o365_cal = O365CalendarClient(auth, cfg.get("o365_group_email") or "")
    request.app.state.o365_tasks = O365TasksClient(
        auth,
        plan_id=cfg.get("o365_planner_plan_id") or "",
        group_email=cfg.get("o365_group_email") or "",
    )
