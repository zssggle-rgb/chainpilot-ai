from __future__ import annotations

from chainpilot_ai.ai.assistant import get_assistant_surface_config


def test_assistant_surface_defaults_to_builtin(monkeypatch) -> None:
    monkeypatch.delenv("CHAINPILOT_ASSISTANT_SURFACE", raising=False)
    result = get_assistant_surface_config()
    assert result["mode"] == "builtin"
    assert result["label"] == "内置业务助手"
    assert result["is_external"] is False


def test_assistant_surface_can_use_goose(monkeypatch) -> None:
    monkeypatch.setenv("CHAINPILOT_ASSISTANT_SURFACE", "goose")
    monkeypatch.setenv("CHAINPILOT_ASSISTANT_URL", "https://goose.example.com")
    result = get_assistant_surface_config()
    assert result["mode"] == "goose"
    assert result["is_external"] is True
    assert result["external_url"] == "https://goose.example.com"
