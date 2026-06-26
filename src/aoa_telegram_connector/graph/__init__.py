"""Build a small conversation graph from normalized Telegram messages."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path


def build_graph(normalized_dir: Path, output_dir: Path, profile_id: str = "starter-permissioned") -> Path:
    nodes: dict[str, dict[str, object]] = {}
    edges: list[dict[str, object]] = []
    for snapshot_path in sorted(normalized_dir.glob("telegram-conversations-*.json")):
        snapshot = json.loads(snapshot_path.read_text(encoding="utf-8"))
        for conversation in snapshot.get("conversations", []):
            conversation_node = f"conversation:{conversation['conversation_id']}"
            nodes[conversation_node] = _node(conversation_node, "conversation", conversation.get("title"), conversation.get("source_url"))
            for message in conversation.get("messages", []):
                message_node = f"message:{message['conversation_id']}:{message['message_id']}"
                nodes[message_node] = _node(message_node, "message", f"Telegram message {message['message_id']}", message.get("source_url"))
                _edge(edges, "conversation_contains_message", conversation_node, message_node, message.get("source_url"), 1.0)
                author = message.get("author", {})
                if isinstance(author, dict) and author.get("id"):
                    author_node = f"author:{author['id']}"
                    nodes.setdefault(author_node, _node(author_node, "author", author.get("label"), message.get("source_url")))
                    _edge(edges, "message_authored_by", message_node, author_node, message.get("source_url"), 0.9)
                if message.get("reply_to_message_id"):
                    target = f"message:{message['conversation_id']}:{message['reply_to_message_id']}"
                    _edge(edges, "message_replies_to_message", message_node, target, message.get("source_url"), 0.9)
                if message.get("edited_at"):
                    _edge(edges, "message_edits_prior_version", message_node, message_node, message.get("source_url"), 0.7)
                if message.get("deleted_at"):
                    _edge(edges, "message_deleted_tombstone", message_node, message_node, message.get("source_url"), 1.0)
                if message.get("pinned"):
                    _edge(edges, "message_pinned_contextualizes_conversation", message_node, conversation_node, message.get("source_url"), 0.8)
                for entity in message.get("entities", []):
                    if not isinstance(entity, dict):
                        continue
                    entity_node = f"entity:{entity.get('kind')}:{entity.get('value')}"
                    nodes.setdefault(entity_node, _node(entity_node, str(entity.get("kind")), str(entity.get("value")), message.get("source_url")))
                    _edge(edges, "message_mentions_entity", message_node, entity_node, message.get("source_url"), 0.6)
                    if entity.get("kind") == "warning":
                        _edge(edges, "message_warns_about_context", message_node, entity_node, message.get("source_url"), 0.8)
                    if entity.get("kind") == "freshness":
                        _edge(edges, "message_supersedes_prior_guidance", message_node, entity_node, message.get("source_url"), 0.7)
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / "graph.json"
    payload = {
        "schema": "aoa_telegram_conversation_graph_v1",
        "profile_id": profile_id,
        "built_at": datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "node_count": len(nodes),
        "edge_count": len(edges),
        "nodes": list(nodes.values()),
        "edges": edges,
    }
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return path


def _node(node_id: str, kind: str, label: object, source_ref: object) -> dict[str, object]:
    return {"schema": "aoa_telegram_graph_node_v1", "node_id": node_id, "kind": kind, "label": str(label or node_id), "source_refs": [str(source_ref or "")]}


def _edge(edges: list[dict[str, object]], kind: str, from_node: str, to_node: str, source_ref: object, confidence: float) -> None:
    edge_id = f"{from_node}->{to_node}:{kind}"
    if any(edge.get("edge_id") == edge_id for edge in edges):
        return
    edges.append(
        {
            "schema": "aoa_telegram_graph_edge_v1",
            "edge_id": edge_id,
            "kind": kind,
            "from_node": from_node,
            "to_node": to_node,
            "source_refs": [str(source_ref or "")],
            "confidence": confidence,
        }
    )
