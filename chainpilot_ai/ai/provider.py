from __future__ import annotations

import json
import os
from time import perf_counter
from typing import Any

import requests

from chainpilot_ai.ai.contracts import LLMConfig, LLMConfigurationError, LLMProviderError, LLMResult

try:
    import frappe
except Exception:  # pragma: no cover - local tests run without a Frappe site.
    frappe = None


def get_llm_config() -> LLMConfig:
    provider = _config_value("chainpilot_llm_provider", "CHAINPILOT_LLM_PROVIDER") or "volcengine_openai"
    base_url = _config_value("chainpilot_llm_base_url", "CHAINPILOT_LLM_BASE_URL") or "https://ark.cn-beijing.volces.com/api/coding/v3"
    api_key = (
        _config_value("chainpilot_llm_api_key", "CHAINPILOT_LLM_API_KEY")
        or os.getenv("ARK_API_KEY")
        or os.getenv("OPENAI_API_KEY")
        or os.getenv("ANTHROPIC_API_KEY")
        or os.getenv("ANTHROPIC_AUTH_TOKEN")
    )
    model = _config_value("chainpilot_llm_model", "CHAINPILOT_LLM_MODEL") or os.getenv("ARK_MODEL") or "MiniMax-M2.5"
    timeout = int(_config_value("chainpilot_llm_timeout_seconds", "CHAINPILOT_LLM_TIMEOUT_SECONDS") or 60)
    if not api_key:
        raise LLMConfigurationError("未配置 LLM API Key。请配置 site_config.chainpilot_llm_api_key 或环境变量 CHAINPILOT_LLM_API_KEY。")
    return LLMConfig(provider=provider, base_url=base_url.rstrip("/"), api_key=api_key, model=model, timeout_seconds=timeout)


def generate_json(
    task_code: str,
    system_prompt: str,
    user_payload: dict[str, Any],
    temperature: float = 0,
    max_tokens: int = 900,
) -> LLMResult:
    config = get_llm_config()
    if config.provider in {"volcengine_openai", "openai_compatible"}:
        return _generate_openai_compatible(config, task_code, system_prompt, user_payload, temperature, max_tokens)
    if config.provider in {"volcengine_anthropic", "anthropic_compatible"}:
        return _generate_anthropic_compatible(config, task_code, system_prompt, user_payload, temperature, max_tokens)
    raise LLMConfigurationError(f"不支持的 LLM provider：{config.provider}")


def health_check() -> dict[str, Any]:
    result = generate_json(
        task_code="LLM_HEALTH_CHECK",
        system_prompt="你是 ChainPilot AI 的连接测试助手。只输出 JSON。",
        user_payload={"task": "请返回 {\"ok\": true, \"message\": \"连接正常\"}。"},
        max_tokens=120,
    )
    return {
        "ok": True,
        "provider": result.provider,
        "model": result.model,
        "duration_ms": result.duration_ms,
        "raw_summary": result.raw_summary,
    }


def _generate_openai_compatible(
    config: LLMConfig,
    task_code: str,
    system_prompt: str,
    user_payload: dict[str, Any],
    temperature: float,
    max_tokens: int,
) -> LLMResult:
    started = perf_counter()
    url = f"{config.base_url}/chat/completions"
    body = {
        "model": config.model,
        "temperature": temperature,
        "max_tokens": max_tokens,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": json.dumps(user_payload, ensure_ascii=False)},
        ],
    }
    response = requests.post(
        url,
        headers={"Authorization": f"Bearer {config.api_key}", "Content-Type": "application/json"},
        json=body,
        timeout=config.timeout_seconds,
    )
    if response.status_code >= 400:
        raise LLMProviderError(f"LLM 调用失败：HTTP {response.status_code}，{_safe_error(response.text)}")
    payload = response.json()
    content = (((payload.get("choices") or [{}])[0].get("message") or {}).get("content") or "").strip()
    usage = payload.get("usage") or {}
    return LLMResult(
        provider=config.provider,
        model=payload.get("model") or config.model,
        content=content,
        raw_summary=_summarize_payload(payload),
        duration_ms=int((perf_counter() - started) * 1000),
        input_tokens=int(usage.get("prompt_tokens") or usage.get("input_tokens") or 0),
        output_tokens=int(usage.get("completion_tokens") or usage.get("output_tokens") or 0),
    )


def _generate_anthropic_compatible(
    config: LLMConfig,
    task_code: str,
    system_prompt: str,
    user_payload: dict[str, Any],
    temperature: float,
    max_tokens: int,
) -> LLMResult:
    started = perf_counter()
    url = f"{config.base_url}/v1/messages"
    response = requests.post(
        url,
        headers={
            "x-api-key": config.api_key,
            "Authorization": f"Bearer {config.api_key}",
            "anthropic-version": "2023-06-01",
            "Content-Type": "application/json",
        },
        json={
            "model": config.model,
            "system": system_prompt,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "messages": [{"role": "user", "content": json.dumps(user_payload, ensure_ascii=False)}],
        },
        timeout=config.timeout_seconds,
    )
    if response.status_code >= 400:
        raise LLMProviderError(f"LLM 调用失败：HTTP {response.status_code}，{_safe_error(response.text)}")
    payload = response.json()
    content_blocks = payload.get("content") or []
    content = "\n".join(block.get("text", "") for block in content_blocks if block.get("type") == "text").strip()
    usage = payload.get("usage") or {}
    return LLMResult(
        provider=config.provider,
        model=payload.get("model") or config.model,
        content=content,
        raw_summary=_summarize_payload(payload),
        duration_ms=int((perf_counter() - started) * 1000),
        input_tokens=int(usage.get("input_tokens") or 0),
        output_tokens=int(usage.get("output_tokens") or 0),
    )


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


def _safe_error(text: str) -> str:
    compact = " ".join((text or "").split())
    return compact[:320]


def _summarize_payload(payload: dict[str, Any]) -> str:
    summary = {
        "id": payload.get("id"),
        "model": payload.get("model"),
        "usage": payload.get("usage"),
    }
    return json.dumps(summary, ensure_ascii=False, sort_keys=True)
