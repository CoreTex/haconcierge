"""HAConcierge – WhatsApp AI Concierge for Home Assistant."""
import logging
import voluptuous as vol

from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import (
    DOMAIN,
    SERVICE_SEND_REPLY,
    ATTR_JID,
    ATTR_TEXT,
    ATTR_QUOTED_MESSAGE_ID,
)

_LOGGER = logging.getLogger(__name__)

CONFIG_SCHEMA = cv.empty_config_schema(DOMAIN)

SEND_REPLY_SCHEMA = vol.Schema({
    vol.Required(ATTR_JID): cv.string,
    vol.Required(ATTR_TEXT): cv.string,
    vol.Optional(ATTR_QUOTED_MESSAGE_ID): cv.string,
})


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Set up HAConcierge integration."""
    hass.data.setdefault(DOMAIN, {})

    # Register the send_reply service for automations
    async def handle_send_reply(call: ServiceCall) -> None:
        jid = call.data[ATTR_JID]
        text = call.data[ATTR_TEXT]
        quoted_id = call.data.get(ATTR_QUOTED_MESSAGE_ID)

        session = async_get_clientsession(hass)
        payload = {"jid": jid, "text": text}
        if quoted_id:
            payload["quoted_message_id"] = quoted_id

        # Call the add-on backend
        addon_url = _get_addon_url(hass)
        try:
            async with session.post(
                f"{addon_url}/api/whatsapp/send",
                json=payload,
                timeout=10,
            ) as resp:
                if resp.status != 200:
                    _LOGGER.error(
                        "haconcierge.send_reply failed: HTTP %d", resp.status
                    )
                else:
                    _LOGGER.debug("WhatsApp reply sent to %s", jid)
        except Exception as e:
            _LOGGER.error("haconcierge.send_reply error: %s", e)

    hass.services.async_register(
        DOMAIN,
        SERVICE_SEND_REPLY,
        handle_send_reply,
        schema=SEND_REPLY_SCHEMA,
    )

    _LOGGER.info("HAConcierge integration loaded")
    return True


def _get_addon_url(hass: HomeAssistant) -> str:
    """Resolve the add-on's ingress URL via Supervisor API."""
    # In Supervisor installations the add-on is reachable at its internal port
    return "http://haconcierge:8099"
