"""Parse Telegram Desktop JSON exports into connector snapshots."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any


TEXT_RE = re.compile(r"\s+", re.UNICODE)
TZ_OFFSET_RE = re.compile(r"[+-]\d{2}:\d{2}$")


def find_export_json(source: Path) -> Path:
    """Return the Telegram Desktop export JSON file for a file or export dir."""

    source = source.expanduser().resolve()
    if source.is_file():
        return source
    candidate = source / "result.json"
    if candidate.is_file():
        return candidate
    raise FileNotFoundError(f"Telegram Desktop export JSON not found: {source}")


def load_telegram_desktop_export(
    source: Path,
    *,
    conversation_id: str | None = None,
    title: str | None = None,
    scope: str = "operator_selected_telegram_desktop_export",
    private: bool = False,
    limit: int | None = None,
) -> dict[str, object]:
    """Load a Telegram Desktop `result.json` export as a normalized snapshot input."""

    export_path = find_export_json(source)
    payload = json.loads(export_path.read_text(encoding="utf-8"))
    messages = [
        _convert_message(message, private=private)
        for message in payload.get("messages", [])
        if isinstance(message, dict)
    ]
    messages = [message for message in messages if message is not None]
    if limit is not None:
        messages = messages[:limit]
    chat_id = conversation_id or _conversation_id(payload, export_path)
    chat_type = _conversation_type(str(payload.get("type") or ""), private=private)
    return {
        "schema": "aoa_telegram_desktop_export_snapshot_v1",
        "source_format": "telegram_desktop_json_export",
        "export_path": str(export_path),
        "conversations": [
            {
                "conversation_id": chat_id,
                "conversation_type": chat_type,
                "title": title or str(payload.get("name") or chat_id),
                "source_url": f"telegram:desktop-export:{chat_id}",
                "scope": scope,
                "allowed_modes": ["takeout_export"],
                "privacy_boundary": "operator-selected Telegram Desktop export",
                "messages": messages,
            }
        ],
    }


def _conversation_id(payload: dict[str, Any], export_path: Path) -> str:
    raw_id = payload.get("id")
    if raw_id is not None:
        return f"tg:desktop-export:{raw_id}"
    stem = re.sub(r"[^a-zA-Z0-9_.-]+", "-", export_path.parent.name).strip("-")
    return f"tg:desktop-export:{stem or 'result'}"


def _conversation_type(raw_type: str, *, private: bool) -> str:
    if private:
        return "private_dm"
    lowered = raw_type.casefold()
    if "personal" in lowered or "private" in lowered:
        return "private_dm"
    if "channel" in lowered:
        return "public_channel"
    if "group" in lowered:
        return "public_group"
    return "telegram_desktop_export"


def _convert_message(message: dict[str, Any], *, private: bool) -> dict[str, object] | None:
    text = _message_text(message.get("text"))
    if not text and not message.get("file") and not message.get("media_type"):
        return None
    message_id = str(message.get("id") or message.get("message_id") or "")
    if not message_id:
        return None
    exported: dict[str, object] = {
        "message_id": message_id,
        "source_url": str(message.get("link") or f"telegram:desktop-export:message:{message_id}"),
        "author": _author(message),
        "posted_at": _date(message.get("date")),
        "edited_at": _date(message.get("edited")),
        "reply_to_message_id": _reply_to(message.get("reply_to_message_id")),
        "visible_in_modes": ["takeout_export"],
        "text": text,
        "entities": _entities(message, text),
        "attachments_metadata": _attachments(message),
    }
    if private:
        exported["sensitivity"] = "private_dm"
    return exported


def _message_text(value: object) -> str:
    if isinstance(value, str):
        return _compact(value)
    if isinstance(value, list):
        parts: list[str] = []
        for item in value:
            if isinstance(item, str):
                parts.append(item)
            elif isinstance(item, dict):
                parts.append(str(item.get("text") or ""))
        return _compact("".join(parts))
    return ""


def _author(message: dict[str, Any]) -> dict[str, str]:
    from_id = str(message.get("from_id") or message.get("actor_id") or "unknown")
    label = str(message.get("from") or message.get("actor") or from_id)
    return {"id": from_id, "label": label, "kind": "telegram_export_author"}


def _date(value: object) -> str | None:
    if value is None:
        return None
    text = str(value)
    if not text:
        return None
    if text.endswith("Z") or TZ_OFFSET_RE.search(text):
        return text
    return f"{text}Z"


def _reply_to(value: object) -> str | None:
    if value in {None, ""}:
        return None
    return str(value)


def _entities(message: dict[str, Any], text: str) -> list[dict[str, str]]:
    entities: list[dict[str, str]] = []
    for item in message.get("text_entities", []):
        if not isinstance(item, dict):
            continue
        kind = str(item.get("type") or "text_entity")
        value = _compact(str(item.get("text") or ""))
        if value:
            entities.append({"kind": kind, "value": value})
    for match in re.findall(r"#[\w_]+", text, flags=re.UNICODE):
        entities.append({"kind": "hashtag", "value": match})
    return _dedupe(entities)


def _attachments(message: dict[str, Any]) -> list[dict[str, object]]:
    keys = ["media_type", "mime_type", "file", "thumbnail", "duration_seconds", "width", "height"]
    if not any(message.get(key) for key in keys):
        return []
    return [
        {
            "kind": str(message.get("media_type") or "attachment"),
            "file_name": str(message.get("file") or message.get("thumbnail") or ""),
            "mime_type": message.get("mime_type"),
            "downloaded": False,
        }
    ]


def _dedupe(entities: list[dict[str, str]]) -> list[dict[str, str]]:
    seen: set[tuple[str, str]] = set()
    deduped: list[dict[str, str]] = []
    for entity in entities:
        key = (entity["kind"], entity["value"].casefold())
        if key in seen:
            continue
        seen.add(key)
        deduped.append(entity)
    return deduped


def _compact(text: str) -> str:
    return TEXT_RE.sub(" ", text).strip()
