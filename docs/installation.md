# HAConcierge – Installationsanleitung

## Voraussetzungen

- Home Assistant mit Supervisor (HA Green, HA Yellow, HA OS, etc.)
- GitHub-Account (kostenlos reicht)
- Ollama auf einem Docker-Server im Heimnetz (empfohlen)
- Optional: Microsoft 365 Business mit Admin-Zugang

---

## Schritt 1: GitHub Repository einrichten

Folge der Anleitung in [github-setup.md](github-setup.md).

---

## Schritt 2: Add-on Repository in HA hinzufügen

1. HA öffnen → **Einstellungen** → **Add-ons**
2. Unten rechts auf **Add-on Store** klicken
3. Drei-Punkte-Menü oben rechts → **Repositories**
4. URL eintragen: `https://github.com/DEIN_USERNAME/haconcierge`
5. **Hinzufügen** → Repository erscheint in der Liste

---

## Schritt 3: Add-on installieren

1. Im Add-on Store nach **HAConcierge** suchen
2. **Installieren** klicken (dauert 3–5 Minuten, Node.js + Python werden installiert)
3. Nach der Installation: **Starten**
4. **Im Sidebar anzeigen** aktivieren (falls nicht automatisch)

---

## Schritt 4: Custom Integration

Die Custom Integration (`haconcierge`) wird beim ersten Add-on-Start **automatisch** in `/config/custom_components/haconcierge/` installiert.

**Danach einmalig:** Home Assistant neu starten (damit die Integration geladen wird).

Füge dann in `configuration.yaml` ein:
```yaml
haconcierge:
```

---

## Schritt 5: WhatsApp einrichten

1. Sidebar → **HAConcierge** öffnen
2. **Einstellungen → WhatsApp**
3. Telefonnummer eingeben (Format: `491701234567` ohne `+`)
4. **OTP anfordern** klicken
5. E-Mail von simquadrat prüfen und 6-stelligen Code eingeben
6. **Bestätigen** → Verbindung wird aufgebaut

> **Tipp:** Falls die Nummer bereits bei WhatsApp registriert ist, nutze stattdessen **Pairing Code**. Dieser wird im WhatsApp-App auf dem Handy eingegeben.

---

## Schritt 6: KI konfigurieren

1. **Einstellungen → KI / AI**
2. Ollama-URL eingeben: `http://192.168.x.x:11434` (IP deines Docker-Servers)
3. **Modelle laden** klicken → verfügbare Modelle werden angezeigt
4. Modell wählen (Standard: `phi3:mini`)
5. **Speichern**

### Ollama auf Docker installieren (falls noch nicht vorhanden)

```bash
docker run -d \
  --name ollama \
  -p 11434:11434 \
  -v ollama:/root/.ollama \
  ollama/ollama

# Modell laden
docker exec -it ollama ollama pull phi3:mini
```

---

## Schritt 7: Besitzer anlegen

1. Sidebar → **Besitzer**
2. **+ Besitzer hinzufügen**
3. Name, Telefonnummer, Aliase (z.B. "Mama, Mutter von Max"), O365-E-Mail
4. Keywords hinzufügen (z.B. "Sport", "Schule", "Arzt")
5. Speichern

---

## Schritt 8: Microsoft 365 (optional)

Folge der Anleitung in [o365-setup.md](o365-setup.md).

---

## Datenschutz-Hinweise

- **Ohne AI-URL**: Keine KI-Verarbeitung, keine externen Anfragen
- **Mit Ollama-URL**: Nachrichten gehen nur an deinen eigenen Docker-Server
- **WhatsApp-Session**: Wird in `/config/haconcierge/sessions/` gespeichert
- **Datenbank**: SQLite in `/config/haconcierge/data/haconcierge.db`
- **Kein Cloud-Zwang**: Alle Komponenten können vollständig lokal betrieben werden
