"""Normalize authorized Telegram fixture snapshots into conversations."""

from __future__ import annotations

import json
import re
from datetime import UTC, datetime
from pathlib import Path


SUPPORTED_MODES = {"bot_api", "tdlib_user_session", "mtproto_user_session", "takeout_export"}
DEFAULT_MODE = "bot_api"


def normalize_snapshot(raw_path: Path, _source_url: str, output_dir: Path, mode: str = DEFAULT_MODE) -> Path:
    if mode not in SUPPORTED_MODES:
        raise ValueError(f"unsupported Telegram ingest mode: {mode}")
    snapshot = json.loads(raw_path.read_text(encoding="utf-8"))
    captured_at = _now()
    conversations = []
    for conversation in snapshot.get("conversations", []):
        normalized_messages = [
            _normalize_message(message, conversation, mode, captured_at)
            for message in conversation.get("messages", [])
            if mode in message.get("visible_in_modes", [])
        ]
        if not normalized_messages:
            continue
        conversations.append(
            {
                "schema": "aoa_telegram_normalized_conversation_v1",
                "source": "telegram",
                "conversation_id": conversation["conversation_id"],
                "conversation_type": conversation["conversation_type"],
                "title": conversation["title"],
                "source_url": conversation.get("source_url"),
                "capture_mode": mode,
                "captured_at": captured_at,
                "authorization_state": _authorization_state(conversation, mode),
                "source_metadata": conversation.get("source_metadata", {}),
                "messages": normalized_messages,
            }
        )
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"telegram-conversations-{mode}.json"
    output_path.write_text(json.dumps({"schema": "aoa_telegram_normalized_snapshot_v1", "conversations": conversations}, indent=2), encoding="utf-8")
    return output_path


def _normalize_message(message: dict[str, object], conversation: dict[str, object], mode: str, captured_at: str) -> dict[str, object]:
    text = str(message.get("text") or "")
    return {
        "schema": "aoa_telegram_normalized_message_v1",
        "source": "telegram",
        "source_mode": mode,
        "conversation_id": conversation["conversation_id"],
        "conversation_type": conversation["conversation_type"],
        "message_id": str(message["message_id"]),
        "source_url": message.get("source_url") or conversation.get("source_url"),
        "author": message.get("author", {}),
        "posted_at": message.get("posted_at"),
        "edited_at": message.get("edited_at"),
        "deleted_at": message.get("deleted_at"),
        "captured_at": captured_at,
        "reply_to_message_id": message.get("reply_to_message_id"),
        "forwarded_from": message.get("forwarded_from"),
        "pinned": bool(message.get("pinned", False)),
        "text": text,
        "entities": _extract_entities(text, message),
        "attachments_metadata": message.get("attachments_metadata", []),
        "media_policy": message.get("media_policy", {"include_media": "none", "downloaded": False}),
        "source_receipt": message.get("source_receipt", {}),
        "permission_state": _permission_state(message, mode),
        "freshness_state": _freshness_state(message),
        "sensitivity": message.get("sensitivity", "public_or_channel_visible"),
    }


def _authorization_state(conversation: dict[str, object], mode: str) -> dict[str, object]:
    allowed_modes = conversation.get("allowed_modes", [])
    return {
        "mode": mode,
        "authorized": mode in allowed_modes,
        "scope": conversation.get("scope"),
        "permission_state": "authorized" if mode in allowed_modes else "insufficient_permission",
        "operator_local": mode in {"tdlib_user_session", "mtproto_user_session", "takeout_export"},
        "privacy_boundary": conversation.get("privacy_boundary", "explicit_allowlist_required"),
    }


def _permission_state(message: dict[str, object], mode: str) -> dict[str, object]:
    private = message.get("sensitivity") in {"private_dm", "closed_group"}
    return {
        "status": "authorized",
        "mode": mode,
        "requires_operator_local_session": private,
        "reason": "connected_account_scope" if private else "configured_allowlist",
    }


def _freshness_state(message: dict[str, object]) -> dict[str, object]:
    if message.get("deleted_at"):
        state = "deleted_tombstone"
    elif message.get("edited_at"):
        state = "edited_message"
    elif message.get("pinned"):
        state = "pinned_context"
    else:
        state = "captured_message"
    return {"state": state, "posted_at": message.get("posted_at"), "edited_at": message.get("edited_at"), "deleted_at": message.get("deleted_at")}


def _extract_entities(text: str, message: dict[str, object]) -> list[dict[str, str]]:
    entities = [{"kind": str(item["kind"]), "value": str(item["value"])} for item in message.get("entities", []) if isinstance(item, dict)]
    lowered = text.casefold()
    for token in ["tdlib", "mtproto", "bot api", "takeout", "xiaomi 13t", "hyperos", "vendor_boot.img", "boot.img", "magisk", "fastboot"]:
        if token in lowered:
            entities.append({"kind": "term", "value": token})
    if any(token in lowered for token in ["warning", "risk", "bootloop", "do not"]):
        entities.append({"kind": "warning", "value": "risk_or_warning"})
    if "supersedes" in lowered or "newer" in lowered:
        entities.append({"kind": "freshness", "value": "superseding_update"})
    if re.search(r"\b(?:boot|vendor_boot|init_boot|recovery)\.img\b", lowered):
        entities.append({"kind": "file", "value": re.search(r"\b(?:boot|vendor_boot|init_boot|recovery)\.img\b", lowered).group(0)})
    return _dedupe_entities(entities)


def _dedupe_entities(entities: list[dict[str, str]]) -> list[dict[str, str]]:
    seen: set[tuple[str, str]] = set()
    result: list[dict[str, str]] = []
    for entity in entities:
        key = (entity["kind"], entity["value"].casefold())
        if key in seen:
            continue
        seen.add(key)
        result.append(entity)
    return result


def _now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")
