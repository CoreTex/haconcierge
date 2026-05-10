import pytest
from config import AppConfig


class TestAppConfig:
    def test_default_values(self, db):
        cfg = AppConfig(db)
        assert cfg.get("ai_model") == "phi3:mini"
        assert cfg.get("ai_provider") == "ollama"
        assert cfg.get("wa_registered") == "false"
        assert cfg.get("o365_enabled") == "false"

    def test_set_and_get(self, db):
        cfg = AppConfig(db)
        cfg.set("ai_model", "mistral:7b")
        assert cfg.get("ai_model") == "mistral:7b"

    def test_set_many(self, db):
        cfg = AppConfig(db)
        cfg.set_many({"ai_model": "llama3.2:3b", "ai_timeout": "60"})
        assert cfg.get("ai_model") == "llama3.2:3b"
        assert cfg.get("ai_timeout") == "60"

    def test_update_existing(self, db):
        cfg = AppConfig(db)
        cfg.set("ai_model", "first")
        cfg.set("ai_model", "second")
        assert cfg.get("ai_model") == "second"

    def test_unknown_key_returns_none(self, db):
        cfg = AppConfig(db)
        assert cfg.get("nonexistent_key") is None

    def test_get_all_returns_all_defaults_and_overrides(self, db):
        cfg = AppConfig(db)
        cfg.set("ai_model", "custom")
        all_cfg = cfg.get_all()
        assert all_cfg["ai_model"] == "custom"
        assert "ai_provider" in all_cfg
        assert "o365_enabled" in all_cfg
