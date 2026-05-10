import logging
import httpx
from typing import Optional

logger = logging.getLogger(__name__)

EVENT_TASK_CREATED = "haconcierge_task_created"
EVENT_APPOINTMENT_CREATED = "haconcierge_appointment_created"
EVENT_KEYWORD_DETECTED = "haconcierge_keyword_detected"


class HAEventClient:
    def __init__(self, ha_url: str, ha_token: str):
        self.ha_url = ha_url.rstrip("/")
        self.token = ha_token
        self._headers = {
            "Authorization": f"Bearer {ha_token}",
            "Content-Type": "application/json",
        }

    async def fire_event(self, event_type: str, data: dict) -> bool:
        url = f"{self.ha_url}/api/events/{event_type}"
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                resp = await client.post(url, json=data, headers=self._headers)
                resp.raise_for_status()
                return True
        except Exception as e:
            logger.error("Failed to fire HA event %s: %s", event_type, e)
            return False

    async def fire_task_event(self, task, message, owner) -> bool:
        return await self.fire_event(EVENT_TASK_CREATED, {
            "task_id": task.id,
            "title": task.title,
            "description": task.description or "",
            "due_date": task.due_date.isoformat() if task.due_date else None,
            "owner_name": owner.name if owner else None,
            "owner_phone": owner.phone if owner else None,
            "source_message": message.content[:500] if message else None,
            "chat_jid": message.chat_jid if message else None,
            "wa_message_id": message.wa_message_id if message else None,
            "sender_name": message.sender_name if message else None,
        })

    async def fire_appointment_event(self, appt, message, owner) -> bool:
        return await self.fire_event(EVENT_APPOINTMENT_CREATED, {
            "appointment_id": appt.id,
            "title": appt.title,
            "description": appt.description or "",
            "start_time": appt.start_time.isoformat(),
            "end_time": appt.end_time.isoformat() if appt.end_time else None,
            "location": appt.location or "",
            "owner_name": owner.name if owner else None,
            "owner_phone": owner.phone if owner else None,
            "source_message": message.content[:500] if message else None,
            "chat_jid": message.chat_jid if message else None,
            "wa_message_id": message.wa_message_id if message else None,
        })

    async def fire_keyword_event(self, keyword_hit, keyword, owner, message) -> bool:
        return await self.fire_event(EVENT_KEYWORD_DETECTED, {
            "keyword": keyword.word,
            "matched_text": keyword_hit.matched_text,
            "owner_name": owner.name if owner else None,
            "owner_phone": owner.phone if owner else None,
            "source_message": message.content[:500] if message else None,
            "chat_jid": message.chat_jid if message else None,
            "wa_message_id": message.wa_message_id if message else None,
            "sender_name": message.sender_name if message else None,
        })

    async def update_sensor(self, entity_id: str, state: str, attributes: dict = None) -> bool:
        url = f"{self.ha_url}/api/states/{entity_id}"
        payload = {"state": state, "attributes": attributes or {}}
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                resp = await client.post(url, json=payload, headers=self._headers)
                return resp.status_code in (200, 201)
        except Exception as e:
            logger.error("Failed to update HA sensor %s: %s", entity_id, e)
            return False
