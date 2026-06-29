"""Small deterministic keyword index for normalized Telegram messages."""

from __future__ import annotations

import json
import re
from collections import Counter, defaultdict
from datetime import UTC, datetime
from pathlib import Path


TOKEN_RE = re.compile(r"[\w.+#/-]+", re.UNICODE)


def build_keyword_index(normalized_dir: Path, output_dir: Path, profile_id: str = "starter-permissioned") -> Path:
    docs: list[dict[str, object]] = []
    permission_gaps: list[dict[str, object]] = []
    for snapshot_path in sorted(normalized_dir.glob("telegram-conversations-*.json")):
        snapshot = json.loads(snapshot_path.read_text(encoding="utf-8"))
        for conversation in snapshot.get("conversations", []):
            auth = conversation.get("authorization_state", {})
            if auth.get("permission_state") != "authorized":
                permission_gaps.append({"conversation_id": conversation.get("conversation_id"), "reason": auth.get("permission_state")})
                continue
            for message in conversation.get("messages", []):
                text = str(message.get("text") or "")
                doc_id = f"message:{message['conversation_id']}:{message['message_id']}"
                docs.append(
                    {
                        "doc_id": doc_id,
                        "source": "telegram",
                        "conversation_id": message.get("conversation_id"),
                        "conversation_type": message.get("conversation_type"),
                        "message_id": message.get("message_id"),
                        "source_url": message.get("source_url"),
                        "source_mode": message.get("source_mode"),
                        "posted_at": message.get("posted_at"),
                        "edited_at": message.get("edited_at"),
                        "captured_at": message.get("captured_at"),
                        "author": message.get("author"),
                        "text": text,
                        "tokens": len(tokenize(text)),
                        "permission_state": message.get("permission_state"),
                        "freshness_state": message.get("freshness_state"),
                        "entities": message.get("entities", []),
                        "attachments_metadata": message.get("attachments_metadata", []),
                        "media_policy": message.get("media_policy", {}),
                        "source_receipt": message.get("source_receipt", {}),
                    }
                )
    inverted: dict[str, list[dict[str, object]]] = defaultdict(list)
    for doc in docs:
        counts = Counter(tokenize(str(doc.get("text") or "")))
        for term, count in sorted(counts.items()):
            inverted[term].append({"doc_id": doc["doc_id"], "count": count})
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / "keyword_index.json"
    payload = {
        "schema": "aoa_telegram_keyword_index_v1",
        "profile_id": profile_id,
        "unit": "telegram_message",
        "built_at": datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "doc_count": len(docs),
        "term_count": len(inverted),
        "docs": docs,
        "inverted": dict(inverted),
        "permission_gaps": permission_gaps,
    }
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return path


def tokenize(text: str) -> list[str]:
    return [token.casefold() for token in TOKEN_RE.findall(text) if token.strip()]
