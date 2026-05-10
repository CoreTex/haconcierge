import logging
from datetime import datetime, timedelta
from typing import Optional
import httpx

from .auth import O365Auth

logger = logging.getLogger(__name__)
GRAPH_BASE = "https://graph.microsoft.com/v1.0"


class O365CalendarClient:
    def __init__(self, auth: O365Auth, group_email: str):
        self.auth = auth
        self.group_email = group_email

    def _headers(self) -> dict:
        token = self.auth.get_token()
        if not token:
            raise RuntimeError("Could not obtain O365 access token")
        return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    async def _get_group_id(self) -> Optional[str]:
        url = f"{GRAPH_BASE}/groups?$filter=mail eq '{self.group_email}'&$select=id,displayName"
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(url, headers=self._headers())
            resp.raise_for_status()
            data = resp.json()
            groups = data.get("value", [])
            return groups[0]["id"] if groups else None

    async def create_event(
        self,
        title: str,
        start: datetime,
        end: Optional[datetime] = None,
        location: Optional[str] = None,
        description: Optional[str] = None,
        attendees: list[str] = None,
    ) -> Optional[str]:
        group_id = await self._get_group_id()
        if not group_id:
            logger.error("O365 group not found for email: %s", self.group_email)
            return None

        if not end:
            end = start + timedelta(hours=1)

        body = {
            "subject": title,
            "body": {"contentType": "Text", "content": description or ""},
            "start": {"dateTime": start.isoformat(), "timeZone": "Europe/Berlin"},
            "end": {"dateTime": end.isoformat(), "timeZone": "Europe/Berlin"},
        }
        if location:
            body["location"] = {"displayName": location}
        if attendees:
            body["attendees"] = [
                {"emailAddress": {"address": email}, "type": "required"}
                for email in attendees
            ]

        url = f"{GRAPH_BASE}/groups/{group_id}/calendar/events"
        try:
            async with httpx.AsyncClient(timeout=15) as client:
                resp = await client.post(url, json=body, headers=self._headers())
                resp.raise_for_status()
                return resp.json().get("id")
        except Exception as e:
            logger.error("Failed to create O365 calendar event: %s", e)
            return None

    async def list_events(self, days_ahead: int = 7) -> list[dict]:
        group_id = await self._get_group_id()
        if not group_id:
            return []
        now = datetime.utcnow()
        end = now + timedelta(days=days_ahead)
        url = (
            f"{GRAPH_BASE}/groups/{group_id}/calendar/events"
            f"?$filter=start/dateTime ge '{now.isoformat()}' and start/dateTime le '{end.isoformat()}'"
            f"&$select=id,subject,start,end,location&$orderby=start/dateTime asc"
        )
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(url, headers=self._headers())
                resp.raise_for_status()
                return resp.json().get("value", [])
        except Exception as e:
            logger.error("Failed to list O365 events: %s", e)
            return []
