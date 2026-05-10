SYSTEM_PROMPT = """Du bist ein intelligenter Assistent der WhatsApp-Nachrichten analysiert.
Antworte IMMER ausschließlich mit validem JSON, niemals mit Text davor oder danach.
Analysiere den Nachrichteninhalt auf Deutsch und Englisch.
Sei konservativ: Erstelle nur Einträge wenn du dir sicher bist.
"""

EXTRACTION_PROMPT = """Analysiere folgende WhatsApp-Nachricht und extrahiere strukturierte Daten.

Bekannte Personen (Besitzer) und ihre Erkennungsmerkmale:
{owners_context}

Nachricht von: {sender_name} ({sender_phone})
Nachrichtentext: {message_text}
Zeitpunkt: {timestamp}

Extrahiere:
1. Termine (Datum+Uhrzeit genannt oder klar impliziert)
2. Aufgaben (explizit oder implizit zugesagt/übernommen)
3. Keywords die einem Besitzer zugeordnet werden können
4. Dem Besitzer zuordnen anhand: direkter Name, Alias, "Mutter/Vater/Kind von X", Beziehungsbegriffe

Antworte NUR mit diesem JSON-Schema:
{{
  "appointments": [
    {{
      "title": "string",
      "description": "string oder null",
      "start_datetime": "ISO8601 oder null",
      "end_datetime": "ISO8601 oder null",
      "location": "string oder null",
      "owner_phone": "Telefonnummer des Besitzers oder null",
      "confidence": 0.0-1.0
    }}
  ],
  "tasks": [
    {{
      "title": "string",
      "description": "string oder null",
      "due_date": "ISO8601-Datum oder null",
      "owner_phone": "Telefonnummer des Besitzers oder null",
      "implicit": true/false,
      "matched_text": "der exakte Textabschnitt der die Aufgabe auslöst",
      "confidence": 0.0-1.0
    }}
  ],
  "keyword_hits": [
    {{
      "keyword": "string",
      "owner_phone": "Telefonnummer des Besitzers",
      "matched_text": "string",
      "confidence": 0.0-1.0
    }}
  ],
  "summary": "Kurze Zusammenfassung auf Deutsch was erkannt wurde oder 'Keine relevanten Daten gefunden'"
}}
"""

IMPLICIT_TASK_PHRASES_DE = [
    "ich kümmere mich",
    "ich erledige",
    "ich mache das",
    "ich übernehme",
    "mache ich",
    "erledige ich",
    "ich bringe",
    "ich hole",
    "ich kaufe",
    "ich schaue",
    "ich frage",
    "ich schreibe",
    "ich rufe an",
    "ich schicke",
    "ich reserviere",
    "ich buche",
    "kein Problem",
    "alles klar",
    "wird gemacht",
    "mache ich gerne",
    "ich spreche",
    "ich klär das",
]

IMPLICIT_TASK_PHRASES_EN = [
    "i'll take care",
    "i'll handle",
    "i'll do it",
    "i'll get it",
    "i'll bring",
    "i'll pick up",
    "i'll buy",
    "i'll check",
    "i'll call",
    "i'll send",
    "i'll book",
    "no problem",
    "will do",
    "on it",
    "got it",
    "i'll sort it",
]
