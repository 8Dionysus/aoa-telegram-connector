"""Operator-local Telegram source registry and sync planning."""

from __future__ import annotations

import hashlib
import json
import re
from datetime import UTC, datetime
from pathlib import Path


SOURCE_KINDS = {"channel", "group", "supergroup", "paid_channel", "paid_group", "private_chat", "saved_messages"}
ACCESS_MODES = {"public", "paid_member", "private_authorized", "self_saved"}
MEDIA_POLICIES = {"none", "thumbnails", "documents", "all"}
REGISTRY_SCHEMA = "aoa_telegram_source_registry_v1"
SOURCE_SCHEMA = "aoa_telegram_source_v1"


def registry_path(data_root: Path) -> Path:
    return data_root / "sources" / "telegram_sources.json"


def load_registry(data_root: Path) -> dict[str, object]:
    path = registry_path(data_root)
    if not path.exists():
        return {"schema": REGISTRY_SCHEMA, "sources": []}
    registry = json.loads(path.read_text(encoding="utf-8"))
    if registry.get("schema") != REGISTRY_SCHEMA:
        raise ValueError(f"unsupported Telegram source registry schema: {registry.get('schema')}")
    if not isinstance(registry.get("sources"), list):
        raise ValueError("Telegram source registry must contain a sources list")
    return registry


def save_registry(data_root: Path, registry: dict[str, object]) -> Path:
    path = registry_path(data_root)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(registry, indent=2, sort_keys=True), encoding="utf-8")
    return path


def upsert_source(
    data_root: Path,
    *,
    source_ref: str,
    kind: str,
    access: str | None = None,
    title: str | None = None,
    tags: list[str] | None = None,
    trust_score: float | None = None,
    include_media: str = "none",
    enabled: bool = True,
    scope: str | None = None,
    notes: str | None = None,
) -> tuple[dict[str, object], Path, str]:
    source_ref = source_ref.strip()
    kind = kind.strip()
    access = _infer_access(kind, access)
    _validate_source(source_ref, kind, access, include_media, trust_score)

    registry = load_registry(data_root)
    sources = [source for source in registry.get("sources", []) if isinstance(source, dict)]
    source_id = _source_id(kind, source_ref)
    now = _now()
    existing = next((source for source in sources if source.get("source_id") == source_id), None)
    descriptor = {
        "schema": SOURCE_SCHEMA,
        "source_id": source_id,
        "source_ref": source_ref,
        "route": f"telegram:mtproto_user_session:{kind}:{source_ref}",
        "kind": kind,
        "access": access,
        "title": title or (existing or {}).get("title") or source_ref,
        "conversation_id": _conversation_id(kind, source_ref),
        "conversation_type": _conversation_type(kind),
        "scope": scope or (existing or {}).get("scope") or f"operator_selected_{kind}",
        "tags": _normalize_tags(tags or list((existing or {}).get("tags", []))),
        "trust_score": _trust_score(trust_score, existing),
        "enabled": bool(enabled),
        "operator_local": True,
        "read_only": True,
        "requires_connected_account": True,
        "media_policy": {"include_media": include_media, "download_default": "disabled"},
        "provenance_policy": "source_receipt_required",
        "created_at": str((existing or {}).get("created_at") or now),
        "updated_at": now,
    }
    if notes:
        descriptor["notes"] = notes
    state = "updated" if existing else "created"
    registry["sources"] = sorted([source for source in sources if source.get("source_id") != source_id] + [descriptor], key=lambda item: str(item.get("source_id")))
    path = save_registry(data_root, registry)
    return descriptor, path, state


def select_sources(
    registry: dict[str, object],
    *,
    source_refs: list[str] | None = None,
    kinds: list[str] | None = None,
    tags: list[str] | None = None,
    enabled_only: bool = True,
) -> list[dict[str, object]]:
    selected: list[dict[str, object]] = []
    refs = {ref.casefold() for ref in source_refs or []}
    kind_filter = set(kinds or [])
    tag_filter = {tag.casefold() for tag in tags or []}
    for source in registry.get("sources", []):
        if not isinstance(source, dict):
            continue
        if enabled_only and not source.get("enabled", True):
            continue
        if refs and str(source.get("source_ref", "")).casefold() not in refs:
            continue
        if kind_filter and source.get("kind") not in kind_filter:
            continue
        source_tags = {str(tag).casefold() for tag in source.get("tags", [])}
        if tag_filter and not (tag_filter & source_tags):
            continue
        selected.append(source)
    return selected


def build_sync_plan(*, run_id: str, sources: list[dict[str, object]], limit: int, include_media: str | None = None) -> dict[str, object]:
    if include_media is not None and include_media not in MEDIA_POLICIES:
        raise ValueError(f"unsupported media policy: {include_media}")
    steps = []
    for source in sources:
        effective_media = include_media or dict(source.get("media_policy", {})).get("include_media") or "none"
        steps.append(
            {
                "source_id": source.get("source_id"),
                "source_ref": source.get("source_ref"),
                "route": source.get("route"),
                "kind": source.get("kind"),
                "access": source.get("access"),
                "conversation_id": source.get("conversation_id"),
                "conversation_type": source.get("conversation_type"),
                "scope": source.get("scope"),
                "tags": source.get("tags", []),
                "trust_score": source.get("trust_score"),
                "include_media": effective_media,
                "download_touched": False,
                "read_only": True,
                "command_hint": [
                    "aoa-telegram",
                    "materialize",
                    "mtproto-history",
                    str(source.get("source_ref")),
                    "--run",
                    f"{run_id}-{source.get('source_id')}",
                    "--limit",
                    str(limit),
                ],
            }
        )
    return {
        "schema": "aoa_telegram_source_sync_plan_v1",
        "run_id": run_id,
        "selected_count": len(steps),
        "steps": steps,
        "network_touched": False,
        "read_only": True,
        "write_touched": False,
        "download_touched": False,
        "created_at": _now(),
    }


def source_private_flag(source: dict[str, object]) -> bool:
    return source.get("kind") in {"private_chat", "saved_messages"} or source.get("access") in {"private_authorized", "self_saved"}


def effective_media_policy(source: dict[str, object], override: str | None = None) -> str:
    value = override or dict(source.get("media_policy", {})).get("include_media") or "none"
    if value not in MEDIA_POLICIES:
        raise ValueError(f"unsupported media policy: {value}")
    return str(value)


def parse_csv(value: str | None) -> list[str]:
    if not value:
        return []
    return [item.strip() for item in value.split(",") if item.strip()]


def _validate_source(source_ref: str, kind: str, access: str, include_media: str, trust_score: float | None) -> None:
    if not source_ref:
        raise ValueError("source_ref is required")
    if kind not in SOURCE_KINDS:
        raise ValueError(f"unsupported Telegram source kind: {kind}")
    if access not in ACCESS_MODES:
        raise ValueError(f"unsupported Telegram access mode: {access}")
    if include_media not in MEDIA_POLICIES:
        raise ValueError(f"unsupported media policy: {include_media}")
    if trust_score is not None and not 0 <= trust_score <= 1:
        raise ValueError("trust_score must be between 0 and 1")


def _infer_access(kind: str, access: str | None) -> str:
    if access:
        return access
    if kind in {"paid_channel", "paid_group"}:
        return "paid_member"
    if kind == "private_chat":
        return "private_authorized"
    if kind == "saved_messages":
        return "self_saved"
    return "public"


def _conversation_type(kind: str) -> str:
    return {
        "channel": "public_channel",
        "group": "public_group",
        "supergroup": "supergroup",
        "paid_channel": "paid_channel",
        "paid_group": "paid_group",
        "private_chat": "private_dm",
        "saved_messages": "saved_messages",
    }[kind]


def _conversation_id(kind: str, source_ref: str) -> str:
    return f"tg:{kind}:{_slug(source_ref)}"


def _source_id(kind: str, source_ref: str) -> str:
    digest = hashlib.sha256(f"{kind}:{source_ref.casefold()}".encode("utf-8")).hexdigest()
    return f"tgsrc-{digest[:16]}"


def _slug(value: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9_.@-]+", "-", value).strip("-")
    return slug or "source"


def _normalize_tags(tags: list[str]) -> list[str]:
    normalized = []
    seen = set()
    for tag in tags:
        item = re.sub(r"\s+", "-", str(tag).strip().casefold())
        if not item or item in seen:
            continue
        seen.add(item)
        normalized.append(item)
    return normalized


def _trust_score(value: float | None, existing: dict[str, object] | None) -> float:
    if value is not None:
        return round(float(value), 3)
    existing_value = (existing or {}).get("trust_score")
    if isinstance(existing_value, int | float):
        return round(float(existing_value), 3)
    return 0.5


def _now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")
