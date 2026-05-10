# 🤵 HAConcierge

**WhatsApp AI Concierge für Home Assistant** – Erkennt automatisch Termine und Aufgaben aus WhatsApp-Nachrichten und synchronisiert sie mit Home Assistant und Microsoft 365.

> Datenschutz-First: Alle Daten werden lokal verarbeitet. KI-Anfragen gehen nur an deinen eigenen, konfigurierten Server. Ohne explizite Konfiguration verlassen keine Daten das Heimnetzwerk.

---

## Features

| Feature | Beschreibung |
|---------|-------------|
| 💬 **WhatsApp** | Direktnachrichten + Gruppen (lesen, antworten mit Quote) |
| 🤖 **Lokale KI** | Ollama-kompatibel, phi3:mini Standard (konfigurierbar) |
| 👨‍👩‍👧‍👦 **Besitzer** | 2–4 Familienmitglieder, Aliase + Keywords |
| 📅 **Termine** | Extraktion + Microsoft 365 Gruppenkalender |
| ✅ **Aufgaben** | Extraktion + Microsoft Planner (geteilt) |
| 🔔 **Events** | HA-Events für Automationen (`haconcierge_task_created` etc.) |
| 🗣️ **Antworten** | Service `haconcierge.send_reply` mit WhatsApp-Zitierfunktion |
| 🔒 **Datenschutz** | Lokal-First, kein Cloud-Zwang |

---

## Installation

Siehe [docs/installation.md](docs/installation.md) für die vollständige Schritt-für-Schritt-Anleitung.

### Kurzfassung

1. **GitHub-Repository erstellen** → [docs/github-setup.md](docs/github-setup.md)
2. In HA: *Einstellungen → Add-ons → Add-on Store → ⋮ → Repositories hinzufügen*
3. URL eintragen: `https://github.com/DEIN_USERNAME/haconcierge`
4. Add-on installieren und starten
5. Sidebar öffnen: **HAConcierge**
6. WhatsApp einrichten → KI konfigurieren → Besitzer anlegen

---

## Architektur

```
HA Sidebar (Ingress)
     │
     ▼
┌─────────────────────────────┐
│   Python FastAPI Backend    │  Port 8099
│   - REST API                │
│   - Jinja2 + htmx Frontend  │
│   - AI Processor (Ollama)   │
│   - HA Event Client         │
│   - O365 Graph API          │
└──────────┬──────────────────┘
           │ HTTP
           ▼
┌─────────────────────────────┐
│  Node.js Baileys Bridge     │  Port 3001 (intern)
│  - WhatsApp Multi-Device    │
│  - Registrierung via SMS    │
│  - Pairing Code Support     │
└─────────────────────────────┘
           │
     WhatsApp Server
```

**Daten-Storage:** `/config/haconcierge/` (persistent, bleibt bei Add-on-Updates)

---

## HA Events für Automationen

### `haconcierge_task_created`
```yaml
# event.data enthält:
task_id: 42
title: "Max von Schule abholen"
owner_name: "Anna"
owner_phone: "491701234567"
wa_message_id: "3EB0B..."  # Für Quote-Antwort
chat_jid: "491701234567@s.whatsapp.net"
```

### `haconcierge_appointment_created`
```yaml
appointment_id: 7
title: "Zahnarzt"
start_time: "2025-06-15T10:00:00"
owner_name: "Anna"
wa_message_id: "3EB0B..."
```

### `haconcierge_keyword_detected`
```yaml
keyword: "Sport"
owner_name: "Anna"
matched_text: "Sport Training heute"
wa_message_id: "3EB0B..."
```

---

## Automation Beispiel

```yaml
automation:
  - alias: "HAConcierge – Aufgabe bestätigen"
    trigger:
      - platform: event
        event_type: haconcierge_task_created
    action:
      - service: haconcierge.send_reply
        data:
          jid: "{{ trigger.event.data.owner_phone }}@s.whatsapp.net"
          text: "✅ Aufgabe erkannt: {{ trigger.event.data.title }}"
          quoted_message_id: "{{ trigger.event.data.wa_message_id }}"
```

---

## Lizenz

MIT License – siehe [LICENSE](LICENSE)
