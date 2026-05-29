from __future__ import annotations

import os
from typing import Any

try:
    import frappe
except Exception:  # pragma: no cover - local tests run without a Frappe site.
    frappe = None


ASSISTANT_SURFACES = {
    "builtin": {
        "label": "内置业务助手",
        "description": "在 ChainPilot 内完成目标理解、建议解释、审批摘要和沟通草稿。",
    },
    "openclaw": {
        "label": "OpenClaw 工作台",
        "description": "跳转到已配置的 OpenClaw 助手，由 ChainPilot 提供业务上下文和结果链接。",
    },
    "goose": {
        "label": "Goose 工作台",
        "description": "跳转到已配置的 Goose 助手，由 ChainPilot 提供业务上下文和结果链接。",
    },
    "custom": {
        "label": "外部智能助手",
        "description": "跳转到企业自定义助手入口，ChainPilot 继续负责算法、证据和审批边界。",
    },
}


def get_assistant_surface_config() -> dict[str, Any]:
    mode = _config_value("chainpilot_assistant_surface", "CHAINPILOT_ASSISTANT_SURFACE") or "builtin"
    mode = mode.strip().lower()
    if mode not in ASSISTANT_SURFACES:
        mode = "builtin"
    preset = ASSISTANT_SURFACES[mode]
    label = _config_value("chainpilot_assistant_label", "CHAINPILOT_ASSISTANT_LABEL") or preset["label"]
    description = _config_value("chainpilot_assistant_description", "CHAINPILOT_ASSISTANT_DESCRIPTION") or preset["description"]
    external_url = _config_value("chainpilot_assistant_url", "CHAINPILOT_ASSISTANT_URL") or ""
    return {
        "mode": mode,
        "label": label,
        "description": description,
        "external_url": external_url,
        "is_external": mode != "builtin",
        "supported_modes": [
            {"mode": key, "label": value["label"], "description": value["description"]}
            for key, value in ASSISTANT_SURFACES.items()
        ],
    }


def _config_value(site_key: str, env_key: str) -> str | None:
    env_value = os.getenv(env_key)
    if env_value:
        return env_value
    try:
        if frappe and getattr(frappe.local, "site", None):
            value = frappe.conf.get(site_key)
            if value:
                return str(value)
    except Exception:
        return None
    return None
