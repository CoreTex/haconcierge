from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import Optional
from database.db import get_db
from database.models import WhatsAppGroup, Message

router = APIRouter(prefix="/api/whatsapp", tags=["whatsapp"])


class RegisterRequest(BaseModel):
    phone: str


class ConfirmCodeRequest(BaseModel):
    phone: str
    code: str


class SendReplyRequest(BaseModel):
    jid: str
    text: str
    quoted_message_id: Optional[str] = None


class GroupMonitorUpdate(BaseModel):
    monitored: bool


@router.get("/status")
async def get_status(request: Request):
    wa_client = request.app.state.wa_client
    status = await wa_client.get_status()
    return status


@router.post("/register/request-code")
async def request_registration_code(body: RegisterRequest, request: Request):
    wa_client = request.app.state.wa_client
    result = await wa_client.request_registration_code(body.phone)
    return result


@router.post("/register/confirm-code")
async def confirm_registration_code(body: ConfirmCodeRequest, request: Request, db: Session = Depends(get_db)):
    wa_client = request.app.state.wa_client
    result = await wa_client.confirm_registration_code(body.phone, body.code)
    if result.get("success"):
        from config import AppConfig
        cfg = AppConfig(db)
        cfg.set("wa_phone", body.phone)
        cfg.set("wa_registered", "true")
    return result


@router.post("/pair/request-code")
async def request_pairing_code(body: RegisterRequest, request: Request):
    wa_client = request.app.state.wa_client
    result = await wa_client.get_pairing_code(body.phone)
    return result


@router.post("/send")
async def send_reply(body: SendReplyRequest, request: Request):
    wa_client = request.app.state.wa_client
    success = await wa_client.send_message(body.jid, body.text, body.quoted_message_id)
    if not success:
        raise HTTPException(500, "Failed to send message")
    return {"success": True}


@router.get("/groups")
async def list_groups(request: Request, db: Session = Depends(get_db)):
    wa_client = request.app.state.wa_client
    # Sync groups from bridge
    live_groups = await wa_client.get_groups()
    from whatsapp.handler import MessageHandler
    handler = request.app.state.msg_handler
    if live_groups:
        await handler.handle_group_sync(live_groups)
    groups = db.query(WhatsAppGroup).all()
    return [
        {
            "id": g.id,
            "jid": g.jid,
            "name": g.name,
            "monitored": g.monitored,
            "participant_count": g.participant_count,
            "last_seen": g.last_seen.isoformat() if g.last_seen else None,
        }
        for g in groups
    ]


@router.put("/groups/{group_id}")
async def update_group(group_id: int, body: GroupMonitorUpdate, db: Session = Depends(get_db)):
    group = db.query(WhatsAppGroup).get(group_id)
    if not group:
        raise HTTPException(404, "Group not found")
    group.monitored = body.monitored
    db.commit()
    return {"success": True}


@router.post("/groups/{group_id}/leave")
async def leave_group(group_id: int, request: Request, db: Session = Depends(get_db)):
    group = db.query(WhatsAppGroup).get(group_id)
    if not group:
        raise HTTPException(404, "Group not found")
    wa_client = request.app.state.wa_client
    success = await wa_client.leave_group(group.jid)
    if success:
        db.delete(group)
        db.commit()
    return {"success": success}


@router.get("/messages")
def list_messages(limit: int = 50, db: Session = Depends(get_db)):
    messages = (
        db.query(Message)
        .order_by(Message.timestamp.desc())
        .limit(limit)
        .all()
    )
    return [
        {
            "id": m.id,
            "chat_jid": m.chat_jid,
            "sender_name": m.sender_name,
            "content": m.content,
            "is_group": m.is_group,
            "timestamp": m.timestamp.isoformat(),
            "processed": m.processed,
            "ai_result": m.ai_result,
        }
        for m in messages
    ]


@router.post("/webhook")
async def webhook(request: Request):
    """Receives incoming messages from the Node.js Baileys bridge."""
    payload = await request.json()
    handler = request.app.state.msg_handler
    import asyncio
    asyncio.create_task(handler.handle_incoming(payload))
    return {"ok": True}
