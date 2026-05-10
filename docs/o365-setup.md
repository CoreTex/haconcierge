# Microsoft 365 Einrichten – HAConcierge

## Überblick

HAConcierge nutzt die **Microsoft Graph API** mit **Client Credentials** (Service-zu-Service, kein Benutzer-Login nötig). Du benötigst Admin-Zugang zu deinem M365 Business Tenant.

---

## Schritt 1: Azure App-Registrierung

1. **Azure Portal** öffnen: https://portal.azure.com
2. Suche: **Microsoft Entra ID** (früher Azure Active Directory)
3. Linkes Menü: **App-Registrierungen** → **Neue Registrierung**

**Formular ausfüllen:**
- Name: `HAConcierge`
- Unterstützte Kontotypen: **Nur diese Organisationsverzeichnis**
- Umleitungs-URI: leer lassen
- **Registrieren**

---

## Schritt 2: Client Secret erstellen

1. Neu erstellte App öffnen
2. Linkes Menü: **Zertifikate & Geheimnisse**
3. **Neuer geheimer Clientschlüssel**
4. Beschreibung: `HAConcierge`, Ablauf: `24 Monate`
5. **Hinzufügen**
6. **WICHTIG:** Den angezeigten Wert sofort kopieren (wird nur einmal angezeigt!)

Notiere dir:
- **Anwendungs-ID (Client-ID)**: Auf der Overview-Seite
- **Verzeichnis-ID (Tenant-ID)**: Auf der Overview-Seite
- **Client Secret**: Gerade kopiert

---

## Schritt 3: API-Berechtigungen

1. Linkes Menü: **API-Berechtigungen** → **Berechtigung hinzufügen**
2. **Microsoft Graph** → **Anwendungsberechtigungen**

Folgende Berechtigungen hinzufügen:
| Berechtigung | Zweck |
|-------------|-------|
| `Calendars.ReadWrite` | Termine im Gruppenkalender erstellen |
| `Group.ReadWrite.All` | Gruppe und Kalender lesen |
| `Tasks.ReadWrite` | Microsoft Planner Aufgaben erstellen |
| `User.Read.All` | Benutzer-IDs für Aufgaben-Zuweisung |

3. Nach dem Hinzufügen: **Administratoreinwilligung für [Tenant] erteilen** klicken
4. Alle Berechtigungen müssen grün (✓) werden

---

## Schritt 4: O365-Gruppe finden

Die Gruppe, die du in O365 angelegt hast, benötigst du in zwei Formen:

**E-Mail-Alias** (für den Kalender):
- In Outlook: Gruppe öffnen → E-Mail-Adresse notieren (z.B. `meinefamilie@firma.de`)

**Planner Plan-ID** (für Aufgaben):
1. https://tasks.office.com öffnen
2. Den Planner-Plan der Gruppe öffnen
3. Aus der URL die Plan-ID kopieren: `.../planner/plan/`**DIESE_ID**`/...`

---

## Schritt 5: In HAConcierge eintragen

1. Sidebar → **Einstellungen → Microsoft 365**
2. Aktivieren ✓
3. Felder ausfüllen:
   - Tenant-ID
   - Client-ID  
   - Client Secret
   - Gruppen E-Mail Alias
   - Planner Plan-ID
4. **Speichern**

---

## Berechtigungsübersicht

```
HAConcierge (App) → Graph API
    ↓
    ├── Gruppen-Kalender (Calendars.ReadWrite)
    │   └── Termine erstellen + Besitzer einladen
    │
    ├── Planner (Tasks.ReadWrite)
    │   └── Aufgaben erstellen + Besitzer zuweisen
    │
    └── User-Lookup (User.Read.All)
        └── O365-Email → User-ID für Zuweisung
```

---

## Sicherheitshinweise

- Der Client Secret ist ein hochsensibles Geheimnis
- Er wird verschlüsselt in der SQLite-DB gespeichert
- Niemals in Git committen oder teilen
- Ablaufende Secrets rechtzeitig erneuern (Kalender-Erinnerung setzen)
- Berechtigungen auf Minimum begrenzen (nur die oben genannten)
