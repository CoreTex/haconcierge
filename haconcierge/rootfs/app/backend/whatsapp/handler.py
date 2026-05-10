import logging
from datetime import datetime
from sqlalchemy.orm import Session

from database.models import Message, Owner, WhatsAppGroup
from ai.processor import MessageProcessor
from homeassistant.events import HAEventClient
from o365.calendar import O365CalendarClient
from o365.tasks import O365TasksClient
from whatsapp.client import WhatsAppBridgeClient
from config import AppConfig

logger = logging.getLogger(__name__)


class MessageHandler:
    def __init__(
        self,
        db: Session,
        processor: MessageProcessor,
        ha_client: HAEventClient,
        wa_client: WhatsAppBridgeClient,
        config: AppConfig,
        o365_cal: O365CalendarClient = None,
        o365_tasks: O365TasksClient = None,
    ):
        self.db = db
        self.processor = processor
        self.ha = ha_client
        self.wa = wa_client
        self.config = config
        self.o365_cal = o365_cal
        self.o365_tasks = o365_tasks

    async def handle_incoming(self, payload: dict) -> None:
        wa_id = payload.get("id")
        if not wa_id:
            return

        # Deduplicate
        existing = self.db.query(Message).filter(Message.wa_message_id == wa_id).first()
        if existing:
            return

        chat_jid = payload.get("chatJid", "")
        is_group = "@g.us" in chat_jid

        # Check if group is monitored
        if is_group:
            group = self.db.query(WhatsAppGroup).filter(WhatsAppGroup.jid == chat_jid).first()
            if group and not group.monitored:
                return

        ts_raw = payload.get("timestamp", 0)
        timestamp = datetime.fromtimestamp(ts_raw) if ts_raw else datetime.utcnow()

        msg = Message(
            wa_message_id=wa_id,
            chat_jid=chat_jid,
            sender_jid=payload.get("senderJid", ""),
            sender_name=payload.get("senderName"),
            content=payload.get("text", ""),
            is_group=is_group,
            timestamp=timestamp,
        )
        self.db.add(msg)
        self.db.flush()

        if not msg.content.strip():
            self.db.commit()
            return

        ai_base_url = self.config.get("ai_base_url") or ""
        if not ai_base_url:
            logger.info("No AI endpoint configured – skipping AI processing")
            self.db.commit()
            return

        result = await self.processor.process(msg)
        created = await self.processor.persist_results(msg, result)

        await self._dispatch_results(created, msg)

    async def _dispatch_results(self, created: dict, msg: Message) -> None:
        owners_by_id = {o.id: o for o in self.db.query(Owner).filter(Owner.active == True).all()}

        for task in created.get("tasks", []):
            owner = owners_by_id.get(task.owner_id) if task.owner_id else None
            # Fire HA event
            await self.ha.fire_task_event(task, msg, owner)
            task.ha_event_fired = True

            # O365 Planner
            if self.o365_tasks and self.config.get("o365_enabled") == "true":
                attendees = [owner.o365_email] if owner and owner.o365_email else []
                o365_id = await self.o365_tasks.create_task(
                    title=task.title,
                    description=task.description or "",
                    due_date=task.due_date,
                    assigned_to=attendees,
                )
                if o365_id:
                    task.o365_task_id = o365_id

            # Notify owner via WhatsApp DM
            if owner and owner.notify_on_task and self.config.get("wa_proactive_notify") == "true":
                text = f"✅ Neue Aufgabe für dich erkannt:\n*{task.title}*"
                if task.description:
                    text += f"\n{task.description}"
                await self.wa.send_message(f"{owner.phone}@s.whatsapp.net", text, msg.wa_message_id)

        for appt in created.get("appointments", []):
            owner = owners_by_id.get(appt.owner_id) if appt.owner_id else None
            await self.ha.fire_appointment_event(appt, msg, owner)
            appt.ha_event_fired = True

            if self.o365_cal and self.config.get("o365_enabled") == "true":
                attendees = [owner.o365_email] if owner and owner.o365_email else []
                o365_id = await self.o365_cal.create_event(
                    title=appt.title,
                    start=appt.start_time,
                    end=appt.end_time,
                    location=appt.location,
                    description=appt.description,
                    attendees=attendees,
                )
                if o365_id:
                    appt.o365_event_id = o365_id

            if owner and owner.notify_on_appointment and self.config.get("wa_proactive_notify") == "true":
                from babel.dates import format_datetime
                dt_str = format_datetime(appt.start_time, format="medium", locale="de_DE")
                text = f"📅 Neuer Termin erkannt:\n*{appt.title}*\n{dt_str}"
                if appt.location:
                    text += f"\n📍 {appt.location}"
                await self.wa.send_message(f"{owner.phone}@s.whatsapp.net", text, msg.wa_message_id)

        for kh_info in created.get("keyword_hits", []):
            hit = kh_info["hit"]
            owner = kh_info.get("owner")
            kw = self.db.query(__import__("database.models", fromlist=["Keyword"]).Keyword).get(hit.keyword_id)
            await self.ha.fire_keyword_event(hit, kw, owner, msg)
            hit.ha_event_fired = True

            if owner and owner.notify_on_keyword and self.config.get("wa_proactive_notify") == "true":
                text = f"🔔 Keyword erkannt: *{kw.word}*\nNachricht: {msg.content[:200]}"
                await self.wa.send_message(f"{owner.phone}@s.whatsapp.net", text, msg.wa_message_id)

        self.db.commit()

    async def handle_group_sync(self, groups: list[dict]) -> None:
        for g in groups:
            jid = g.get("id", "")
            existing = self.db.query(WhatsAppGroup).filter(WhatsAppGroup.jid == jid).first()
            if existing:
                existing.name = g.get("name", existing.name)
                existing.participant_count = g.get("participantCount", existing.participant_count)
                existing.last_seen = datetime.utcnow()
            else:
                self.db.add(WhatsAppGroup(
                    jid=jid,
                    name=g.get("name", jid),
                    participant_count=g.get("participantCount", 0),
                    monitored=True,
                    last_seen=datetime.utcnow(),
                ))
        self.db.commit()
