import httpx
import logging
from typing import Optional

logger = logging.getLogger(__name__)


class WhatsAppBridgeClient:
    """HTTP client to communicate with the Node.js Baileys bridge."""

    def __init__(self, bridge_url: str):
        self.url = bridge_url.rstrip("/")

    async def send_message(self, jid: str, text: str, quoted_id: Optional[str] = None) -> bool:
        payload = {"jid": jid, "text": text}
        if quoted_id:
            payload["quotedId"] = quoted_id
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.post(f"{self.url}/send", json=payload)
                resp.raise_for_status()
                return True
        except Exception as e:
            logger.error("Failed to send WhatsApp message to %s: %s", jid, e)
            return False

    async def get_status(self) -> dict:
        try:
            async with httpx.AsyncClient(timeout=3) as client:
                resp = await client.get(f"{self.url}/status")
                return resp.json()
        except Exception:
            return {"connected": False, "status": "unreachable"}

    async def get_groups(self) -> list[dict]:
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(f"{self.url}/groups")
                resp.raise_for_status()
                return resp.json().get("groups", [])
        except Exception as e:
            logger.error("Failed to get groups: %s", e)
            return []

    async def leave_group(self, jid: str) -> bool:
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.post(f"{self.url}/groups/leave", json={"jid": jid})
                resp.raise_for_status()
                return True
        except Exception as e:
            logger.error("Failed to leave group %s: %s", jid, e)
            return False

    async def request_registration_code(self, phone: str) -> dict:
        """Request OTP via SMS for a fresh WhatsApp registration."""
        try:
            async with httpx.AsyncClient(timeout=15) as client:
                resp = await client.post(
                    f"{self.url}/register/request-code",
                    json={"phone": phone},
                )
                return resp.json()
        except Exception as e:
            logger.error("Failed to request registration code: %s", e)
            return {"success": False, "error": str(e)}

    async def confirm_registration_code(self, phone: str, code: str) -> dict:
        """Submit OTP to complete WhatsApp registration."""
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.post(
                    f"{self.url}/register/confirm-code",
                    json={"phone": phone, "code": code},
                )
                return resp.json()
        except Exception as e:
            logger.error("Failed to confirm registration code: %s", e)
            return {"success": False, "error": str(e)}

    async def get_pairing_code(self, phone: str) -> dict:
        """Get pairing code for linking an existing WhatsApp account."""
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.post(
                    f"{self.url}/pair/request-code",
                    json={"phone": phone},
                )
                return resp.json()
        except Exception as e:
            logger.error("Failed to get pairing code: %s", e)
            return {"success": False, "error": str(e)}

    async def disconnect(self) -> bool:
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                resp = await client.post(f"{self.url}/disconnect")
                return resp.status_code == 200
        except Exception:
            return False
