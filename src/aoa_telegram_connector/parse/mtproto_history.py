"""Read-only MTProto history adapter for operator-authorized Telegram chats."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


TEXT_RE = re.compile(r"\s+", re.UNICODE)


@dataclass(frozen=True)
class MtprotoCredentials:
    api_id: int
    api_hash: str
    phone: str | None = None


async def load_mtproto_history(
    *,
    chat: str,
    credentials: MtprotoCredentials,
    session_path: Path,
    limit: int,
    conversation_id: str | None = None,
    title: str | None = None,
    scope: str = "operator_selected_mtproto_history",
    private: bool = False,
    conversation_type: str | None = None,
    source_metadata: dict[str, object] | None = None,
    include_media: str = "none",
) -> dict[str, object]:
    """Fetch a bounded chat history through Telethon without downloading media."""

    try:
        from telethon import TelegramClient
    except ModuleNotFoundError as exc:  # pragma: no cover - exercised only without optional extra.
        raise RuntimeError("Telethon is required: install aoa-telegram-connector[api]") from exc

    session_path = session_path.expanduser().resolve()
    session_path.parent.mkdir(parents=True, exist_ok=True)
    messages: list[dict[str, object]] = []
    async with TelegramClient(str(session_path), credentials.api_id, credentials.api_hash) as client:
        if not await client.is_user_authorized():
            await client.start(phone=credentials.phone)
        entity = await client.get_entity(chat)
        async for message in client.iter_messages(entity, limit=limit, reverse=True):
            converted = mtproto_message_to_snapshot_message(message, private=private, include_media=include_media)
            if converted is not None:
                messages.append(converted)
    chat_id = conversation_id or f"tg:mtproto:{_slug(chat)}"
    resolved_conversation_type = conversation_type or ("private_dm" if private else "mtproto_chat")
    return {
        "schema": "aoa_telegram_mtproto_history_snapshot_v1",
        "source_format": "telegram_mtproto_history",
        "chat": chat,
        "session_path": str(session_path),
        "limit": limit,
        "media_policy": {"include_media": include_media, "download_default": "disabled"},
        "conversations": [
            {
                "conversation_id": chat_id,
                "conversation_type": resolved_conversation_type,
                "title": title or chat,
                "source_url": f"telegram:mtproto:{chat_id}",
                "scope": scope,
                "allowed_modes": ["mtproto_user_session"],
                "privacy_boundary": "operator-selected MTProto connected-account history",
                "source_metadata": source_metadata or {},
                "messages": messages,
            }
        ],
    }


def mtproto_message_to_snapshot_message(message: Any, *, private: bool = False, include_media: str = "none") -> dict[str, object] | None:
    """Convert a Telethon message-like object into connector snapshot format."""

    text = _compact(str(getattr(message, "raw_text", "") or getattr(message, "message", "") or ""))
    message_id = getattr(message, "id", None)
    if message_id is None:
        return None
    if not text and not _media_metadata(message):
        return None
    exported: dict[str, object] = {
        "message_id": str(message_id),
        "source_url": f"telegram:mtproto:message:{message_id}",
        "author": _author(message),
        "posted_at": _date(getattr(message, "date", None)),
        "edited_at": _date(getattr(message, "edit_date", None)),
        "reply_to_message_id": _reply_to(getattr(message, "reply_to_msg_id", None)),
        "visible_in_modes": ["mtproto_user_session"],
        "text": text,
        "entities": _entities(message, text),
        "attachments_metadata": _media_metadata(message),
        "media_policy": {"include_media": include_media, "downloaded": False},
        "source_receipt": {
            "adapter": "telethon.iter_messages",
            "source_mode": "mtproto_user_session",
            "message_id": str(message_id),
            "network_touched": True,
            "read_only": True,
            "download_touched": False,
        },
    }
    if private:
        exported["sensitivity"] = "private_dm"
    return exported


def _author(message: Any) -> dict[str, str]:
    sender_id = getattr(message, "sender_id", None) or getattr(message, "from_id", None) or "unknown"
    return {"id": str(sender_id), "label": str(sender_id), "kind": "mtproto_sender"}


def _date(value: object) -> str | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        if value.tzinfo is None:
            value = value.replace(tzinfo=UTC)
        return value.astimezone(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    text = str(value)
    return text or None


def _reply_to(value: object) -> str | None:
    if value in {None, ""}:
        return None
    return str(value)


def _entities(message: Any, text: str) -> list[dict[str, str]]:
    entities: list[dict[str, str]] = []
    for item in getattr(message, "entities", None) or []:
        entities.append({"kind": type(item).__name__, "value": type(item).__name__})
    for match in re.findall(r"#[\w_]+", text, flags=re.UNICODE):
        entities.append({"kind": "hashtag", "value": match})
    return _dedupe(entities)


def _media_metadata(message: Any) -> list[dict[str, object]]:
    media = getattr(message, "media", None)
    file_info = getattr(message, "file", None)
    if media is None and file_info is None:
        return []
    return [
        {
            "kind": type(media).__name__ if media is not None else "attachment",
            "file_name": str(getattr(file_info, "name", "") or ""),
            "mime_type": getattr(file_info, "mime_type", None),
            "size": getattr(file_info, "size", None),
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


def _slug(value: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9_.@-]+", "-", value).strip("-")
    return slug or "chat"


def _compact(text: str) -> str:
    return TEXT_RE.sub(" ", text).strip()
