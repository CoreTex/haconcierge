import logging
import os
import asyncio
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from database.db import init_db, get_db, SessionLocal
from database.models import Settings
from config import AppConfig, get_env_config
from ai.client import AIClient
from ai.processor import MessageProcessor
from whatsapp.client import WhatsAppBridgeClient
from whatsapp.handler import MessageHandler
from homeassistant.events import HAEventClient
from api.routes import owners, whatsapp, settings as settings_router, dashboard

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(name)s %(levelname)s %(message)s",
)
logger = logging.getLogger("haconcierge")

TEMPLATES_DIR = os.path.join(os.path.dirname(__file__), "templates")
STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("HAConcierge starting up...")
    init_db()

    env = get_env_config()
    db = SessionLocal()
    cfg = AppConfig(db)

    # Initialize HA event client
    app.state.ha_client = HAEventClient(
        ha_url=env["ha_url"],
        ha_token=env["ha_token"],
    )

    # Initialize WhatsApp bridge client
    app.state.wa_client = WhatsAppBridgeClient(env["whatsapp_bridge_url"])

    # Initialize AI client (if configured)
    ai_url = cfg.get("ai_base_url") or ""
    if ai_url:
        app.state.ai_client = AIClient(
            base_url=ai_url,
            model=cfg.get("ai_model") or "phi3:mini",
            timeout=int(cfg.get("ai_timeout") or 30),
            temperature=float(cfg.get("ai_temperature") or 0.1),
        )
    else:
        app.state.ai_client = None
        logger.info("No AI endpoint configured – AI processing disabled")

    # Initialize O365 clients (if configured)
    app.state.o365_cal = None
    app.state.o365_tasks = None
    if cfg.get("o365_enabled") == "true":
        from o365.auth import O365Auth
        from o365.calendar import O365CalendarClient
        from o365.tasks import O365TasksClient
        auth = O365Auth(
            tenant_id=cfg.get("o365_tenant_id") or "",
            client_id=cfg.get("o365_client_id") or "",
            client_secret=cfg.get("o365_client_secret") or "",
        )
        app.state.o365_cal = O365CalendarClient(auth, cfg.get("o365_group_email") or "")
        app.state.o365_tasks = O365TasksClient(
            auth,
            plan_id=cfg.get("o365_planner_plan_id") or "",
            group_email=cfg.get("o365_group_email") or "",
        )

    # Initialize message processor and handler
    processor = MessageProcessor(
        ai_client=app.state.ai_client,
        db=db,
    )
    app.state.msg_handler = MessageHandler(
        db=db,
        processor=processor,
        ha_client=app.state.ha_client,
        wa_client=app.state.wa_client,
        config=cfg,
        o365_cal=app.state.o365_cal,
        o365_tasks=app.state.o365_tasks,
    )
    app.state.config = cfg
    db.close()

    # Update HA sensor on startup
    asyncio.create_task(
        app.state.ha_client.update_sensor(
            "sensor.haconcierge_status",
            "running",
            {"friendly_name": "HAConcierge", "icon": "mdi:robot"},
        )
    )

    yield

    logger.info("HAConcierge shutting down...")


app = FastAPI(title="HAConcierge", lifespan=lifespan)

# Static files
if os.path.exists(STATIC_DIR):
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

templates = Jinja2Templates(directory=TEMPLATES_DIR)

# API routes
app.include_router(dashboard.router)
app.include_router(owners.router)
app.include_router(whatsapp.router)
app.include_router(settings_router.router)


# Frontend page routes
@app.get("/", response_class=HTMLResponse)
async def page_dashboard(request: Request):
    return templates.TemplateResponse("pages/dashboard.html", {"request": request})


@app.get("/owners", response_class=HTMLResponse)
async def page_owners(request: Request):
    return templates.TemplateResponse("pages/owners.html", {"request": request})


@app.get("/groups", response_class=HTMLResponse)
async def page_groups(request: Request):
    return templates.TemplateResponse("pages/groups.html", {"request": request})


@app.get("/messages", response_class=HTMLResponse)
async def page_messages(request: Request):
    return templates.TemplateResponse("pages/messages.html", {"request": request})


@app.get("/tasks", response_class=HTMLResponse)
async def page_tasks(request: Request):
    return templates.TemplateResponse("pages/tasks.html", {"request": request})


@app.get("/appointments", response_class=HTMLResponse)
async def page_appointments(request: Request):
    return templates.TemplateResponse("pages/appointments.html", {"request": request})


@app.get("/settings", response_class=HTMLResponse)
async def page_settings_redirect():
    return RedirectResponse("/settings/whatsapp")


@app.get("/settings/whatsapp", response_class=HTMLResponse)
async def page_settings_whatsapp(request: Request):
    return templates.TemplateResponse("pages/settings_whatsapp.html", {"request": request})


@app.get("/settings/ai", response_class=HTMLResponse)
async def page_settings_ai(request: Request):
    return templates.TemplateResponse("pages/settings_ai.html", {"request": request})


@app.get("/settings/o365", response_class=HTMLResponse)
async def page_settings_o365(request: Request):
    return templates.TemplateResponse("pages/settings_o365.html", {"request": request})


@app.get("/health")
async def health():
    return {"status": "ok"}


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8099,
        log_level=os.environ.get("LOG_LEVEL", "info"),
    )
