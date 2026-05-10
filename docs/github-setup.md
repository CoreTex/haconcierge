# GitHub Repository einrichten

## Schritt 1: GitHub Account erstellen (falls noch nicht vorhanden)

1. https://github.com/join
2. E-Mail, Benutzername, Passwort eingeben
3. E-Mail bestätigen

---

## Schritt 2: Neues Repository erstellen

1. https://github.com/new
2. Repository-Name: `haconcierge`
3. **Public** auswählen (HACS-Requirement für kostenlose Repositories)
4. **Create repository** klicken

---

## Schritt 3: Dateien anpassen

Ersetze `YOUR_GITHUB_USERNAME` durch deinen echten GitHub-Benutzernamen in diesen Dateien:

- `repository.yaml` → `url: https://github.com/DEIN_USERNAME/haconcierge`
- `haconcierge/config.yaml` → `image: "ghcr.io/DEIN_USERNAME/haconcierge-{arch}"`
- `custom_components/haconcierge/manifest.json` → `codeowners`, `documentation`, `issue_tracker`

---

## Schritt 4: GitHub CLI installieren und anmelden (auf deinem Mac)

```bash
# Homebrew
brew install gh

# Anmelden
gh auth login
# → GitHub.com → HTTPS → Y (Credentials) → Browser
```

---

## Schritt 5: Projekt nach GitHub pushen

```bash
cd "/Users/edorr/Documents/Documents - MacBookProM1/Github/whatsapp_ai_agent_homeassistant"

# Git initialisieren
git init
git branch -M main

# Remote hinzufügen (DEIN_USERNAME ersetzen!)
git remote add origin https://github.com/DEIN_USERNAME/haconcierge.git

# Alles hinzufügen und committen
git add .
git commit -m "Initial release: HAConcierge v1.0.0"

# Pushen
git push -u origin main
```

---

## Schritt 6: GitHub Container Registry aktivieren

Docker Images werden automatisch über GitHub Actions gebaut und in der **GitHub Container Registry (ghcr.io)** gespeichert.

1. Repository → **Settings** → **Actions** → **General**
2. Unter **Workflow permissions**: **Read and write permissions** aktivieren
3. **Save**

Beim nächsten Push auf `main` wird automatisch für `aarch64`, `amd64` und `armv7` gebaut.

---

## Schritt 7: Ersten Build triggern

```bash
# Kleinen Commit machen um CI zu starten
git commit --allow-empty -m "Trigger CI build"
git push
```

Build-Status: `https://github.com/DEIN_USERNAME/haconcierge/actions`

Warte bis alle 3 Architekturen grün sind (~10–15 Minuten beim ersten Mal).

---

## Schritt 8: HACS Custom Repository

In Home Assistant:
1. HACS → ⋮ → **Eigene Repositories**
2. URL: `https://github.com/DEIN_USERNAME/haconcierge`
3. Kategorie: **Add-on**
4. **Hinzufügen**

Jetzt erscheint HAConcierge im Add-on Store.

---

## Updates veröffentlichen

```bash
# Version in config.yaml erhöhen
# Dann:
git add .
git commit -m "Release v1.x.x: ..."
git tag v1.x.x
git push && git push --tags
```
