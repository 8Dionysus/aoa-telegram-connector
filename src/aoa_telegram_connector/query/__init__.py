"""Query Telegram message indexes and optional graph context."""

from __future__ import annotations

import hashlib
import json
import math
import re
from datetime import UTC, datetime
from pathlib import Path

from aoa_telegram_connector.index import tokenize


def packet_id_for_query(query: str) -> str:
    digest = hashlib.sha256(query.strip().encode("utf-8")).hexdigest()
    return f"query-{digest[:16]}"


def query_keyword_index(index_path: Path, query: str, limit: int = 5) -> dict[str, object]:
    index = json.loads(index_path.read_text(encoding="utf-8"))
    docs = {doc["doc_id"]: doc for doc in index.get("docs", [])}
    terms = tokenize(query)
    scores: dict[str, dict[str, object]] = {}
    for term in terms:
        hits = index.get("inverted", {}).get(term, [])
        if not hits:
            continue
        idf = math.log(1 + (max(1, len(docs)) - len(hits) + 0.5) / (len(hits) + 0.5))
        for hit in hits:
            doc_id = str(hit["doc_id"])
            entry = scores.setdefault(doc_id, {"score": 0.0, "matched_terms": set()})
            entry["score"] += float(hit["count"]) * idf
            entry["matched_terms"].add(term)
    ranked = sorted(scores.items(), key=lambda item: (item[1]["score"], len(item[1]["matched_terms"])), reverse=True)[:limit]
    results = []
    for doc_id, score in ranked:
        doc = docs[doc_id]
        matched_terms = sorted(score["matched_terms"])
        results.append(
            {
                "source": "telegram",
                "source_url": doc.get("source_url"),
                "source_mode": doc.get("source_mode"),
                "conversation_id": doc.get("conversation_id"),
                "conversation_type": doc.get("conversation_type"),
                "message_id": doc.get("message_id"),
                "posted_at": doc.get("posted_at"),
                "edited_at": doc.get("edited_at"),
                "captured_at": doc.get("captured_at"),
                "author": doc.get("author"),
                "snippet": _focused_snippet(str(doc.get("text") or ""), matched_terms),
                "score": round(float(score["score"]), 6),
                "matched_terms": matched_terms,
                "evidence_refs": [doc_id, f"telegram-message:{doc.get('message_id')}"],
                "permission_state": doc.get("permission_state"),
                "freshness_state": doc.get("freshness_state"),
                "entities": doc.get("entities", []),
                "attachments_metadata": doc.get("attachments_metadata", []),
                "media_policy": doc.get("media_policy", {}),
                "source_receipt": doc.get("source_receipt", {}),
            }
        )
    permission_status = "ok" if results or not index.get("permission_gaps") else "insufficient_permission"
    return {
        "schema": "aoa_telegram_evidence_packet_v1",
        "packet_id": packet_id_for_query(query),
        "query": query,
        "created_at": datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "query_report": {"algorithm": "bm25_exact_message_v1", "unit": index.get("unit"), "terms": terms},
        "permission_report": {"status": permission_status, "gaps": index.get("permission_gaps", [])},
        "results": results,
        "policy": {"source": "local_message_index", "internal_search_used": False},
        "network_touched": False,
        "read_only": True,
    }


def query_graph_packet(index_path: Path, graph_path: Path, query: str, limit: int = 5) -> dict[str, object]:
    packet = query_keyword_index(index_path, query, limit)
    graph = json.loads(graph_path.read_text(encoding="utf-8"))
    edges = [edge for edge in graph.get("edges", []) if isinstance(edge, dict)]
    for result in packet.get("results", []):
        message_node = f"message:{result.get('conversation_id')}:{result.get('message_id')}"
        result["graph_context"] = {
            "message_node_id": message_node,
            "relation_edges": [edge for edge in edges if edge.get("from_node") == message_node or edge.get("to_node") == message_node],
        }
    packet["policy"]["source"] = "local_message_index_plus_graph"
    packet["graph_report"] = {"graph_path": str(graph_path), "node_count": graph.get("node_count"), "edge_count": graph.get("edge_count")}
    return packet


def _focused_snippet(text: str, needles: list[str], radius: int = 180) -> str:
    lowered = text.casefold()
    positions = [lowered.find(term) for term in needles if term and lowered.find(term) >= 0]
    if not positions:
        return re.sub(r"\s+", " ", text[: radius * 2]).strip()
    start = max(0, min(positions) - radius)
    end = min(len(text), min(positions) + radius)
    return re.sub(r"\s+", " ", text[start:end]).strip()
