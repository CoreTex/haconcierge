import pytest
import asyncio
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

from ai.processor import MessageProcessor
from ai.client import AIClient
from database.models import Message, Owner, Keyword


class TestMessageProcessor:
    def _make_processor(self, db, ai_response: str):
        mock_client = MagicMock(spec=AIClient)
        mock_client.chat = AsyncMock(return_value=ai_response)
        return MessageProcessor(ai_client=mock_client, db=db)

    def _make_message(self, db, content: str, sender_jid: str = "491701234567@s.whatsapp.net"):
        msg = Message(
            wa_message_id="test_id_001",
            chat_jid="491701234567@s.whatsapp.net",
            sender_jid=sender_jid,
            sender_name="Anna",
            content=content,
            is_group=False,
            timestamp=datetime.utcnow(),
        )
        db.add(msg)
        db.flush()
        return msg

    def test_keyword_detection_local(self, db, sample_keyword):
        """Keywords are detected locally without AI."""
        processor = self._make_processor(db, '{"appointments":[],"tasks":[],"keyword_hits":[],"summary":""}')
        msg = self._make_message(db, "Heute haben wir Sport Training um 18 Uhr.")
        result = asyncio.get_event_loop().run_until_complete(processor.process(msg))
        hits = result.get("keyword_hits", [])
        assert any(h["keyword"] == "Sport" for h in hits), "Keyword 'Sport' should be detected"

    def test_no_keyword_in_unrelated_message(self, db, sample_keyword):
        """No false positive keyword detection."""
        processor = self._make_processor(db, '{"appointments":[],"tasks":[],"keyword_hits":[],"summary":""}')
        msg = self._make_message(db, "Kannst du bitte Milch kaufen?")
        result = asyncio.get_event_loop().run_until_complete(processor.process(msg))
        hits = result.get("keyword_hits", [])
        assert len(hits) == 0

    def test_parse_datetime_iso(self):
        from ai.processor import MessageProcessor
        dt = MessageProcessor._parse_datetime("2025-12-24T18:00:00")
        assert dt is not None
        assert dt.day == 24
        assert dt.month == 12

    def test_parse_datetime_date_only(self):
        from ai.processor import MessageProcessor
        dt = MessageProcessor._parse_datetime("2025-06-15")
        assert dt is not None
        assert dt.year == 2025

    def test_parse_datetime_none(self):
        from ai.processor import MessageProcessor
        assert MessageProcessor._parse_datetime(None) is None
        assert MessageProcessor._parse_datetime("") is None
        assert MessageProcessor._parse_datetime("invalid") is None

    def test_implicit_task_detection(self, db):
        from ai.processor import MessageProcessor
        p = MessageProcessor.__new__(MessageProcessor)
        assert p._has_implicit_task("Ich kümmere mich darum") is True
        assert p._has_implicit_task("Ich erledige das heute") is True
        assert p._has_implicit_task("Kein Problem, mache ich") is True
        assert p._has_implicit_task("Das Wetter ist schön") is False

    def test_persist_results_creates_task(self, db, sample_owner):
        """persist_results should create a Task from AI output."""
        processor = self._make_processor(db, "{}")
        msg = self._make_message(db, "Ich hole Max von der Schule ab.")

        result = {
            "appointments": [],
            "tasks": [{
                "title": "Max von Schule abholen",
                "description": None,
                "due_date": None,
                "owner_phone": sample_owner.phone,
                "implicit": True,
                "matched_text": "Ich hole Max von der Schule ab",
                "confidence": 0.9,
            }],
            "keyword_hits": [],
            "summary": "Aufgabe erkannt",
        }

        created = asyncio.get_event_loop().run_until_complete(
            processor.persist_results(msg, result)
        )
        assert len(created["tasks"]) == 1
        assert created["tasks"][0].title == "Max von Schule abholen"
        assert created["tasks"][0].owner_id == sample_owner.id

    def test_persist_results_skips_low_confidence(self, db, sample_owner):
        """Tasks below MIN_CONFIDENCE should not be created."""
        processor = self._make_processor(db, "{}")
        msg = self._make_message(db, "Vielleicht hole ich ihn ab.")

        result = {
            "appointments": [],
            "tasks": [{
                "title": "Evtl. abholen",
                "confidence": 0.3,  # Below threshold
                "owner_phone": sample_owner.phone,
            }],
            "keyword_hits": [],
            "summary": "",
        }

        created = asyncio.get_event_loop().run_until_complete(
            processor.persist_results(msg, result)
        )
        assert len(created["tasks"]) == 0

    def test_persist_results_creates_appointment(self, db, sample_owner):
        """persist_results should create an Appointment from AI output."""
        processor = self._make_processor(db, "{}")
        msg = self._make_message(db, "Arzttermin am 20. Mai um 10 Uhr.")

        result = {
            "appointments": [{
                "title": "Arzttermin",
                "description": None,
                "start_datetime": "2025-05-20T10:00:00",
                "end_datetime": None,
                "location": None,
                "owner_phone": sample_owner.phone,
                "confidence": 0.95,
            }],
            "tasks": [],
            "keyword_hits": [],
            "summary": "Termin erkannt",
        }

        created = asyncio.get_event_loop().run_until_complete(
            processor.persist_results(msg, result)
        )
        assert len(created["appointments"]) == 1
        assert created["appointments"][0].title == "Arzttermin"
