# Changelog

## 1.0.0 - 2025-05-10

### Added
- Initial release
- WhatsApp client via Baileys (multi-device, no browser needed)
- WhatsApp registration flow with manual OTP input (simquadrat / SMS-to-email)
- Local AI processing via Ollama (configurable endpoint)
- Support for multiple AI models (phi3:mini default)
- Owner management with phone numbers, aliases and keywords
- Automatic task and appointment extraction from messages
- Implicit commitment detection ("ich kümmere mich darum")
- Microsoft 365 integration (Planner tasks, Group Calendar)
- Home Assistant events for tasks, appointments and keywords
- `haconcierge.send_reply` service for automations with WhatsApp quoting
- Sidebar panel via HA Ingress
- Privacy-first: all data processed locally unless external server explicitly configured
