import json
from dataclasses import dataclass
from uuid import uuid4

import httpx
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.entities import SysConfig, User
from app.services.audit import log_action

LLM_CONFIG_KEYS = {
    "LLM_ENABLED": {"value": "false", "description": "是否启用大模型合同解析兜底", "is_secret": 0},
    "LLM_ACTIVE_PROFILE": {"value": "default", "description": "当前使用的大模型配置 ID", "is_secret": 0},
    "LLM_PROFILES": {"value": "[]", "description": "大模型配置列表", "is_secret": 1},
    "LLM_API_KEY": {"value": "", "description": "兼容旧版本的 API Key", "is_secret": 1},
    "LLM_API_BASE_URL": {"value": "https://api.openai.com/v1", "description": "兼容旧版本的 API Base URL", "is_secret": 0},
    "LLM_MODEL": {"value": "gpt-4o-mini", "description": "兼容旧版本的模型名称", "is_secret": 0},
}


@dataclass
class LLMRuntimeConfig:
    enabled: bool
    api_key: str
    api_base_url: str
    model: str
    source: str
    profile_id: str = "default"
    profile_name: str = "默认模型"


def _bool_text(value: bool | str | None) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    return "true" if str(value or "").strip().lower() in {"1", "true", "yes", "on"} else "false"


def _mask_secret(value: str | None) -> str:
    if not value:
        return ""
    if len(value) <= 8:
        return "*" * len(value)
    return f"{value[:4]}{'*' * max(len(value) - 8, 4)}{value[-4:]}"


def _rows_by_key(db: Session) -> dict[str, SysConfig]:
    ensure_default_configs(db)
    return {item.config_key: item for item in db.query(SysConfig).filter(SysConfig.config_key.in_(LLM_CONFIG_KEYS)).all()}


def _row_value(rows: dict[str, SysConfig], key: str, default: str = "") -> str:
    row = rows.get(key)
    if row and row.config_value is not None:
        return str(row.config_value)
    return default


def _env_default_profile() -> dict:
    settings = get_settings()
    return {
        "id": "default",
        "name": "默认模型",
        "api_base_url": settings.llm_api_base_url,
        "model": settings.llm_model,
        "api_key": settings.llm_api_key or "",
    }


def _normalize_profile(profile: dict, fallback: dict | None = None) -> dict:
    fallback = fallback or {}
    profile_id = str(profile.get("id") or fallback.get("id") or uuid4().hex[:12])
    return {
        "id": profile_id,
        "name": str(profile.get("name") or fallback.get("name") or "未命名模型").strip(),
        "api_base_url": str(profile.get("api_base_url") or fallback.get("api_base_url") or "https://api.openai.com/v1").strip().rstrip("/"),
        "model": str(profile.get("model") or fallback.get("model") or "gpt-4o-mini").strip(),
        "api_key": str(profile.get("api_key") or fallback.get("api_key") or "").strip(),
    }


def _load_profiles(rows: dict[str, SysConfig]) -> list[dict]:
    env_profile = _env_default_profile()
    legacy_profile = _normalize_profile(
        {
            "id": "default",
            "name": "默认模型",
            "api_base_url": _row_value(rows, "LLM_API_BASE_URL", env_profile["api_base_url"]),
            "model": _row_value(rows, "LLM_MODEL", env_profile["model"]),
            "api_key": _row_value(rows, "LLM_API_KEY", env_profile["api_key"]),
        }
    )
    raw = _row_value(rows, "LLM_PROFILES", "[]")
    try:
        parsed = json.loads(raw) if raw else []
    except json.JSONDecodeError:
        parsed = []
    profiles = [_normalize_profile(item) for item in parsed if isinstance(item, dict)]
    if not profiles:
        profiles = [legacy_profile]
    elif not any(item["id"] == "default" for item in profiles):
        profiles.insert(0, legacy_profile)
    return profiles


def _public_profile(profile: dict) -> dict:
    return {
        "id": profile["id"],
        "name": profile["name"],
        "api_base_url": profile["api_base_url"],
        "model": profile["model"],
        "has_api_key": bool(profile.get("api_key")),
        "api_key_masked": _mask_secret(profile.get("api_key")),
    }


def ensure_default_configs(db: Session) -> None:
    existing = {item.config_key for item in db.query(SysConfig).filter(SysConfig.config_key.in_(LLM_CONFIG_KEYS)).all()}
    for key, meta in LLM_CONFIG_KEYS.items():
        if key in existing:
            continue
        db.add(
            SysConfig(
                config_key=key,
                config_value=meta["value"],
                config_type="llm",
                description=meta["description"],
                is_secret=meta["is_secret"],
            )
        )


def get_llm_runtime_config(db: Session | None = None) -> LLMRuntimeConfig:
    settings = get_settings()
    if db is None:
        return LLMRuntimeConfig(
            enabled=settings.llm_enabled,
            api_key=settings.llm_api_key or "",
            api_base_url=settings.llm_api_base_url.rstrip("/"),
            model=settings.llm_model,
            source="env",
        )
    rows = _rows_by_key(db)
    profiles = _load_profiles(rows)
    active_id = _row_value(rows, "LLM_ACTIVE_PROFILE", profiles[0]["id"])
    active = next((item for item in profiles if item["id"] == active_id), profiles[0])
    return LLMRuntimeConfig(
        enabled=_bool_text(_row_value(rows, "LLM_ENABLED", "true" if settings.llm_enabled else "false")) == "true",
        api_key=active.get("api_key", ""),
        api_base_url=active.get("api_base_url", settings.llm_api_base_url).rstrip("/"),
        model=active.get("model", settings.llm_model),
        source="database",
        profile_id=active["id"],
        profile_name=active["name"],
    )


def get_llm_config_payload(db: Session) -> dict:
    rows = _rows_by_key(db)
    profiles = _load_profiles(rows)
    active_id = _row_value(rows, "LLM_ACTIVE_PROFILE", profiles[0]["id"])
    if not any(item["id"] == active_id for item in profiles):
        active_id = profiles[0]["id"]
    return {
        "enabled": _bool_text(_row_value(rows, "LLM_ENABLED", "false")) == "true",
        "active_profile_id": active_id,
        "profiles": [_public_profile(item) for item in profiles],
        "source": "database",
    }


def update_llm_config(
    db: Session,
    user: User,
    enabled: bool,
    profiles: list[dict],
    active_profile_id: str | None = None,
) -> dict:
    rows = _rows_by_key(db)
    old_profiles = {item["id"]: item for item in _load_profiles(rows)}
    normalized: list[dict] = []
    for profile in profiles:
        fallback = old_profiles.get(str(profile.get("id") or ""))
        next_profile = _normalize_profile(profile, fallback)
        if not profile.get("api_key") and fallback:
            next_profile["api_key"] = fallback.get("api_key", "")
        normalized.append(next_profile)
    if not normalized:
        normalized = [_normalize_profile({}, _env_default_profile())]
    active_id = active_profile_id or normalized[0]["id"]
    if not any(item["id"] == active_id for item in normalized):
        active_id = normalized[0]["id"]
    updates = {
        "LLM_ENABLED": _bool_text(enabled),
        "LLM_ACTIVE_PROFILE": active_id,
        "LLM_PROFILES": json.dumps(normalized, ensure_ascii=False),
    }
    active = next(item for item in normalized if item["id"] == active_id)
    updates.update(
        {
            "LLM_API_BASE_URL": active["api_base_url"],
            "LLM_MODEL": active["model"],
            "LLM_API_KEY": active.get("api_key", ""),
        }
    )
    for key, value in updates.items():
        row = rows.get(key)
        if row is None:
            meta = LLM_CONFIG_KEYS[key]
            row = SysConfig(config_key=key, config_type="llm", description=meta["description"], is_secret=meta["is_secret"])
            db.add(row)
        row.config_value = value
        row.update_by = user.id
    log_action(db, user, "system_llm_config_update", f"enabled:{updates['LLM_ENABLED']} active_profile:{active_id} profiles:{len(normalized)}")
    db.commit()
    return get_llm_config_payload(db)


def runtime_from_profile(enabled: bool, profile: dict, fallback: LLMRuntimeConfig | None = None) -> LLMRuntimeConfig:
    fallback_profile = {
        "id": fallback.profile_id if fallback else "request",
        "name": fallback.profile_name if fallback else "测试模型",
        "api_base_url": fallback.api_base_url if fallback else "https://api.openai.com/v1",
        "model": fallback.model if fallback else "gpt-4o-mini",
        "api_key": fallback.api_key if fallback else "",
    }
    normalized = _normalize_profile(profile, fallback_profile)
    if not profile.get("api_key") and fallback:
        normalized["api_key"] = fallback.api_key
    return LLMRuntimeConfig(
        enabled=enabled,
        api_key=normalized["api_key"],
        api_base_url=normalized["api_base_url"],
        model=normalized["model"],
        source="request",
        profile_id=normalized["id"],
        profile_name=normalized["name"],
    )


def test_llm_connection(config: LLMRuntimeConfig) -> dict:
    if not config.enabled:
        return {"reachable": False, "message": "LLM 未启用", "profile_id": config.profile_id}
    if not config.api_key:
        return {"reachable": False, "message": "LLM API Key 未配置", "profile_id": config.profile_id}
    url = f"{config.api_base_url.rstrip('/')}/chat/completions"
    payload = {
        "model": config.model,
        "messages": [
            {"role": "system", "content": "只返回 JSON。"},
            {"role": "user", "content": "返回 {\"ok\": true}"},
        ],
        "temperature": 0,
        "max_tokens": 20,
        "response_format": {"type": "json_object"},
    }
    headers = {"Authorization": f"Bearer {config.api_key}", "Content-Type": "application/json"}
    try:
        response = httpx.post(url, headers=headers, json=payload, timeout=30)
        response.raise_for_status()
        return {"reachable": True, "message": "LLM 连接测试成功", "model": config.model, "profile_id": config.profile_id}
    except Exception as exc:
        return {"reachable": False, "message": str(exc), "model": config.model, "profile_id": config.profile_id}
