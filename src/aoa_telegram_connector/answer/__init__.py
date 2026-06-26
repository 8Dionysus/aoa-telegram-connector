"""Render permission-aware answer packets from Telegram evidence packets."""

from __future__ import annotations


def render_answer_packet(evidence_packet: dict[str, object], limit: int = 5) -> dict[str, object]:
    results = [result for result in evidence_packet.get("results", [])[:limit] if isinstance(result, dict)]
    permission_report = evidence_packet.get("permission_report", {})
    if results:
        answer_status = "answered"
    elif isinstance(permission_report, dict) and permission_report.get("status") == "insufficient_permission":
        answer_status = "insufficient_permission"
    else:
        answer_status = "insufficient_evidence"
    evidence_chain = [_chain_item(result) for result in results]
    warning_supported = any(_has_warning(result) for result in results)
    edited_or_deleted = any(_freshness_state(result) in {"edited_message", "deleted_tombstone"} for result in results)
    return {
        "schema": "aoa_connector_answer_packet_v1",
        "answer_id": str(evidence_packet.get("packet_id", "query")).replace("query-", "answer-", 1),
        "query": evidence_packet.get("query", ""),
        "created_at": evidence_packet.get("created_at"),
        "answer_report": {
            "renderer": "telegram_permissioned_conversation_answer_v1",
            "answer_status": answer_status,
            "source_packet_id": evidence_packet.get("packet_id"),
            "candidate_result_count": len(results),
        },
        "answers": [_answer_item(result) for result in results],
        "evidence_chain": evidence_chain,
        "permission_report": permission_report,
        "conflict_report": {"status": "conflict_or_warning_pressure" if warning_supported else answer_status, "warning_supported": warning_supported},
        "freshness_report": {"status": "edited_or_deleted_context" if edited_or_deleted else answer_status, "states": sorted({_freshness_state(result) for result in results})},
        "applicability_report": {"status": answer_status, "source_modes": sorted({str(result.get("source_mode")) for result in results})},
        "warning_report": {"status": "warning_supported" if warning_supported else answer_status},
        "agent_answer": _agent_answer(answer_status, evidence_chain),
        "policy": {"source": "local_message_index_plus_graph_answer_renderer", "internal_search_used": False},
        "network_touched": False,
        "read_only": True,
    }


def _answer_item(result: dict[str, object]) -> dict[str, object]:
    return {
        "answer_kind": "telegram_message_evidence",
        "answer_text": result.get("snippet"),
        "source_url": result.get("source_url"),
        "conversation_id": result.get("conversation_id"),
        "message_id": result.get("message_id"),
        "source_mode": result.get("source_mode"),
    }


def _chain_item(result: dict[str, object]) -> dict[str, object]:
    graph_context = result.get("graph_context", {})
    edges = graph_context.get("relation_edges", []) if isinstance(graph_context, dict) else []
    return {
        "source": "telegram",
        "source_url": result.get("source_url"),
        "conversation_id": result.get("conversation_id"),
        "message_id": result.get("message_id"),
        "source_mode": result.get("source_mode"),
        "permission_state": result.get("permission_state"),
        "freshness_state": result.get("freshness_state"),
        "relation_kinds": sorted({str(edge.get("kind")) for edge in edges if isinstance(edge, dict)}),
        "evidence_refs": result.get("evidence_refs", []),
    }


def _freshness_state(result: dict[str, object]) -> str:
    freshness = result.get("freshness_state", {})
    return str(freshness.get("state", "unknown")) if isinstance(freshness, dict) else "unknown"


def _has_warning(result: dict[str, object]) -> bool:
    entities = result.get("entities", [])
    if any(isinstance(entity, dict) and entity.get("kind") == "warning" for entity in entities):
        return True
    graph_context = result.get("graph_context", {})
    edges = graph_context.get("relation_edges", []) if isinstance(graph_context, dict) else []
    return any(isinstance(edge, dict) and "warn" in str(edge.get("kind", "")) for edge in edges)


def _agent_answer(status: str, evidence_chain: list[dict[str, object]]) -> str:
    if status == "answered":
        first = evidence_chain[0] if evidence_chain else {}
        return f"Local Telegram evidence supports an answer from {first.get('conversation_id')} message {first.get('message_id')}."
    if status == "insufficient_permission":
        return "The local Telegram connector lacks permission for the requested scope."
    return "The local Telegram connector does not have enough local evidence for this question."
