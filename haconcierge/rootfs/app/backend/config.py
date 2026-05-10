import json
import os
from typing import Optional
from sqlalchemy.orm import Session
from database.models import Settings


class AppConfig:
    """Runtime configuration stored in SQLite, not in HA options."""

    DEFAULTS = {
        # AI
        "ai_provider": "ollama",
        "ai_base_url": "",  # e.g. http://192.168.1.100:11434
        "ai_model": "phi3:mini",
        "ai_timeout": "30",
        "ai_temperature": "0.1",
        # WhatsApp
        "wa_phone": "",
        "wa_registered": "false",
        "wa_proactive_notify": "true",
        # O365
        "o365_enabled": "false",
        "o365_tenant_id": "",
        "o365_client_id": "",
        "o365_client_secret": "",
        "o365_group_email": "",
        "o365_planner_plan_id": "",
        # Privacy
        "privacy_mode": "strict",  # strict = block all external, relaxed = warn
    }

    def __init__(self, db: Session):
        self._db = db

    def get(self, key: str) -> Optional[str]:
        row = self._db.query(Settings).filter(Settings.key == key).first()
        if row:
            return row.value
        return self.DEFAULTS.get(key)

    def set(self, key: str, value: str) -> None:
        row = self._db.query(Settings).filter(Settings.key == key).first()
        if row:
            row.value = value
        else:
            self._db.add(Settings(key=key, value=value))
        self._db.commit()

    def get_all(self) -> dict:
        rows = self._db.query(Settings).all()
        result = dict(self.DEFAULTS)
        for row in rows:
            result[row.key] = row.value
        return result

    def set_many(self, data: dict) -> None:
        for key, value in data.items():
            self.set(key, str(value))


def get_env_config() -> dict:
    return {
        "ha_token": os.environ.get("HA_TOKEN", ""),
        "ha_url": os.environ.get("HA_URL", "http://supervisor/core"),
        "data_dir": os.environ.get("DATA_DIR", "/config/haconcierge/data"),
        "session_dir": os.environ.get("SESSION_DIR", "/config/haconcierge/sessions"),
        "log_level": os.environ.get("LOG_LEVEL", "info"),
        "whatsapp_bridge_url": os.environ.get("WHATSAPP_BRIDGE_URL", "http://127.0.0.1:3001"),
    }
