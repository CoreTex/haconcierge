import pytest
import asyncio
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

from whatsapp.handler import MessageHandler
from database.models import Message, WhatsAppGroup, Owner


class TestMessageHandler:
    def _make_handler(self, db, processor=None, ha_client=None, wa_client=None, config=None):
        if processor is None:
            processor = MagicMock()
            processor.process = AsyncMock(return_value={
                "appointments": [], "tasks": [], "keyword_hits": [], "summary": ""
            })
            processor.persist_results = AsyncMock(return_value={
                "appointments": [], "tasks": [], "keyword_hits": []
            })
        if ha_client is None:
            ha_client = MagicMock()
            ha_client.fire_task_event = AsyncMock(return_value=True)
            ha_client.fire_appointment_event = AsyncMock(return_value=True)
            ha_client.fire_keyword_event = AsyncMock(return_value=True)
        if wa_client is None:
            wa_client = MagicMock()
            wa_client.send_message = AsyncMock(return_value=True)
        if config is None:
            config = MagicMock()
            config.get = MagicMock(side_effect=lambda k: {
                "ai_base_url": "http://localhost:11434",
                "wa_proactive_notify": "false",
                "o365_enabled": "false",
            }.get(k))

        return MessageHandler(
            db=db, processor=processor, ha_client=ha_client,
            wa_client=wa_client, config=config
        )

    def test_handle_incoming_creates_message(self, db):
        handler = self._make_handler(db)
        payload = {
            "id": "abc123",
            "chatJid": "491701234567@s.whatsapp.net",
            "senderJid": "491701234567@s.whatsapp.net",
            "senderName": "Test",
            "text": "Hallo Welt",
            "isGroup": False,
            "timestamp": datetime.utcnow().timestamp(),
        }
        asyncio.get_event_loop().run_until_complete(handler.handle_incoming(payload))
        msg = db.query(Message).filter(Message.wa_message_id == "abc123").first()
        assert msg is not None
        assert msg.content == "Hallo Welt"

    def test_handle_incoming_deduplicates(self, db):
        handler = self._make_handler(db)
        payload = {
            "id": "dup123",
            "chatJid": "491701234567@s.whatsapp.net",
            "senderJid": "491701234567@s.whatsapp.net",
            "senderName": "Test",
            "text": "Hallo",
            "timestamp": datetime.utcnow().timestamp(),
        }
        asyncio.get_event_loop().run_until_complete(handler.handle_incoming(payload))
        asyncio.get_event_loop().run_until_complete(handler.handle_incoming(payload))
        count = db.query(Message).filter(Message.wa_message_id == "dup123").count()
        assert count == 1

    def test_unmonitored_group_is_ignored(self, db):
        group = WhatsAppGroup(jid="group1@g.us", name="Test Gruppe", monitored=False)
        db.add(group)
        db.commit()

        handler = self._make_handler(db)
        payload = {
            "id": "grp_msg_001",
            "chatJid": "group1@g.us",
            "senderJid": "491701234567@s.whatsapp.net",
            "senderName": "Test",
            "text": "Nachricht in pausierter Gruppe",
            "timestamp": datetime.utcnow().timestamp(),
        }
        asyncio.get_event_loop().run_until_complete(handler.handle_incoming(payload))
        msg = db.query(Message).filter(Message.wa_message_id == "grp_msg_001").first()
        assert msg is None

    def test_group_sync_creates_groups(self, db):
        handler = self._make_handler(db)
        groups = [
            {"id": "g1@g.us", "name": "Gruppe 1", "participantCount": 5},
            {"id": "g2@g.us", "name": "Gruppe 2", "participantCount": 12},
        ]
        asyncio.get_event_loop().run_until_complete(handler.handle_group_sync(groups))
        assert db.query(WhatsAppGroup).count() == 2

    def test_group_sync_updates_existing(self, db):
        db.add(WhatsAppGroup(jid="g1@g.us", name="Alt", participant_count=3))
        db.commit()

        handler = self._make_handler(db)
        asyncio.get_event_loop().run_until_complete(
            handler.handle_group_sync([{"id": "g1@g.us", "name": "Neu", "participantCount": 10}])
        )
        g = db.query(WhatsAppGroup).filter(WhatsAppGroup.jid == "g1@g.us").first()
        assert g.name == "Neu"
        assert g.participant_count == 10
