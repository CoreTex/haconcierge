import json
import logging
import re
from datetime import datetime, date
from typing import Optional
from sqlalchemy.orm import Session

from .client import AIClient
from .prompts import SYSTEM_PROMPT, EXTRACTION_PROMPT, IMPLICIT_TASK_PHRASES_DE, IMPLICIT_TASK_PHRASES_EN
from database.models import Owner, Keyword, Message, Task, Appointment, KeywordHit

logger = logging.getLogger(__name__)

MIN_CONFIDENCE = 0.6


class MessageProcessor:
    def __init__(self, ai_client: AIClient, db: Session):
        self.ai = ai_client
        self.db = db

    def _build_owners_context(self) -> str:
        owners = self.db.query(Owner).filter(Owner.active == True).all()
        lines = []
        for owner in owners:
            aliases = ", ".join(owner.aliases or [])
            kws = [k.word for k in owner.keywords if k.active]
            keywords_str = ", ".join(kws) if kws else "keine"
            lines.append(
                f"- {owner.name} (Telefon: {owner.phone})"
                f"{f', Aliase: {aliases}' if aliases else ''}"
                f", Keywords: {keywords_str}"
            )
        return "\n".join(lines) if lines else "Keine Besitzer konfiguriert."

    def _has_implicit_task(self, text: str) -> bool:
        text_lower = text.lower()
        for phrase in IMPLICIT_TASK_PHRASES_DE + IMPLICIT_TASK_PHRASES_EN:
            if phrase in text_lower:
                return True
        return False

    def _find_keyword_hits(self, text: str) -> list[dict]:
        hits = []
        keywords = (
            self.db.query(Keyword)
            .join(Owner)
            .filter(Keyword.active == True, Owner.active == True)
            .all()
        )
        for kw in keywords:
            flags = 0 if kw.case_sensitive else re.IGNORECASE
            if re.search(re.escape(kw.word), text, flags):
                hits.append({"keyword_id": kw.id, "word": kw.word, "owner": kw.owner})
        return hits

    async def process(self, message: Message, owner_dm=None) -> dict:
        owners_context = self._build_owners_context()
        today = date.today()
        weekdays_de = ["Montag", "Dienstag", "Mittwoch", "Donnerstag", "Freitag", "Samstag", "Sonntag"]

        if owner_dm:
            dm_context = (
                f"HINWEIS: Diese Nachricht ist eine direkte Eingabe von Besitzer '{owner_dm.name}' "
                f"(Telefon: {owner_dm.phone}) an den Concierge. "
                f"Weise alle erkannten Termine und Aufgaben diesem Besitzer zu "
                f"(owner_phone: {owner_dm.phone}). "
                f"Sei bei der Erkennung großzügig – der Besitzer gibt bewusst Daten ein."
            )
        else:
            dm_context = ""

        prompt = EXTRACTION_PROMPT.format(
            owners_context=owners_context,
            sender_name=message.sender_name or "Unbekannt",
            sender_phone=message.sender_jid.split("@")[0],
            message_text=message.content,
            timestamp=message.timestamp.isoformat(),
            today_date=today.isoformat(),
            today_weekday=weekdays_de[today.weekday()],
            dm_context=dm_context,
        )

        raw = await self.ai.chat(
            messages=[{"role": "user", "content": prompt}],
            system=SYSTEM_PROMPT,
        )

        result = {"appointments": [], "tasks": [], "keyword_hits": [], "summary": ""}

        if raw is None:
            logger.warning("AI returned no response (timeout?) for message: %s", message.content[:100])
        elif raw:
            try:
                # Strip markdown code fences if present
                cleaned = re.sub(r"```(?:json)?\s*|\s*```", "", raw).strip()
                result = json.loads(cleaned)
                if result.get("summary"):
                    logger.info("AI summary: %s", result["summary"])
            except json.JSONDecodeError:
                logger.warning("AI returned non-JSON: %s", raw[:200])

        # Keyword detection always runs locally (no AI needed)
        local_hits = self._find_keyword_hits(message.content)
        for hit in local_hits:
            existing = any(
                kh.get("keyword") == hit["word"] for kh in result.get("keyword_hits", [])
            )
            if not existing:
                result.setdefault("keyword_hits", []).append({
                    "keyword": hit["word"],
                    "owner_phone": hit["owner"].phone,
                    "matched_text": hit["word"],
                    "confidence": 1.0,
                })

        return result

    async def persist_results(self, message: Message, result: dict) -> dict:
        created = {"tasks": [], "appointments": [], "keyword_hits": []}
        owners = {o.phone: o for o in self.db.query(Owner).filter(Owner.active == True).all()}

        for appt in result.get("appointments", []):
            if appt.get("confidence", 0) < MIN_CONFIDENCE:
                logger.debug("Appointment below confidence threshold (%.2f): %s", appt.get("confidence", 0), appt.get("title"))
                continue
            owner = owners.get(appt.get("owner_phone", ""))
            start = self._parse_datetime(appt.get("start_datetime"))
            if not start:
                logger.warning(
                    "Appointment '%s' dropped – AI returned no parseable start_datetime (got: %r). "
                    "Check if the model resolved the relative date correctly.",
                    appt.get("title"), appt.get("start_datetime")
                )
                continue
            a = Appointment(
                title=appt["title"],
                description=appt.get("description"),
                owner_id=owner.id if owner else None,
                source_message_id=message.id,
                start_time=start,
                end_time=self._parse_datetime(appt.get("end_datetime")),
                location=appt.get("location"),
            )
            self.db.add(a)
            self.db.flush()
            created["appointments"].append(a)

        for task in result.get("tasks", []):
            if task.get("confidence", 0) < MIN_CONFIDENCE:
                continue
            owner = owners.get(task.get("owner_phone", ""))
            t = Task(
                title=task["title"],
                description=task.get("description"),
                owner_id=owner.id if owner else None,
                source_message_id=message.id,
                due_date=self._parse_datetime(task.get("due_date")),
            )
            self.db.add(t)
            self.db.flush()
            created["tasks"].append(t)

        for kh in result.get("keyword_hits", []):
            if kh.get("confidence", 0) < MIN_CONFIDENCE:
                continue
            owner = owners.get(kh.get("owner_phone", ""))
            kw = (
                self.db.query(Keyword)
                .filter(Keyword.word == kh["keyword"])
                .first()
            )
            if kw:
                hit = KeywordHit(
                    keyword_id=kw.id,
                    message_id=message.id,
                    matched_text=kh.get("matched_text", kh["keyword"]),
                )
                self.db.add(hit)
                self.db.flush()
                created["keyword_hits"].append({"hit": hit, "owner": owner})

        message.processed = True
        message.ai_result = result
        self.db.commit()

        return created

    @staticmethod
    def _parse_datetime(value: Optional[str]) -> Optional[datetime]:
        if not value:
            return None
        formats = [
            "%Y-%m-%dT%H:%M:%S",
            "%Y-%m-%dT%H:%M:%SZ",
            "%Y-%m-%dT%H:%M",
            "%Y-%m-%d",
        ]
        for fmt in formats:
            try:
                return datetime.strptime(value[:19], fmt)
            except ValueError:
                continue
        return None
