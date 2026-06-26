from pathlib import Path

from aoa_telegram_connector.answer import render_answer_packet
from aoa_telegram_connector.graph import build_graph
from aoa_telegram_connector.index import build_keyword_index
from aoa_telegram_connector.normalize import normalize_snapshot
from aoa_telegram_connector.query import query_graph_packet


FIXTURE = Path("connector/fixtures/telegram/starter_conversation.json")


def _build(tmp_path: Path, mode: str = "tdlib_user_session") -> tuple[Path, Path]:
    normalized_dir = tmp_path / "normalized"
    normalize_snapshot(FIXTURE, "telegram:fixture", normalized_dir, mode=mode)
    index_path = build_keyword_index(normalized_dir, tmp_path / "index")
    graph_path = build_graph(normalized_dir, tmp_path / "graph")
    return index_path, graph_path


def test_graph_contains_conversation_edges(tmp_path: Path) -> None:
    _, graph_path = _build(tmp_path)
    graph_text = graph_path.read_text(encoding="utf-8")
    assert "conversation_contains_message" in graph_text
    assert "message_replies_to_message" in graph_text
    assert "message_edits_prior_version" in graph_text
    assert "message_warns_about_context" in graph_text


def test_answer_packet_reports_warning_and_permissions(tmp_path: Path) -> None:
    index_path, graph_path = _build(tmp_path)
    packet = query_graph_packet(index_path, graph_path, "vendor_boot bootloop warning Xiaomi 13T")
    answer = render_answer_packet(packet)
    assert answer["schema"] == "aoa_connector_answer_packet_v1"
    assert answer["network_touched"] is False
    assert answer["read_only"] is True
    assert answer["answer_report"]["answer_status"] == "answered"
    assert answer["warning_report"]["status"] == "warning_supported"
    assert answer["evidence_chain"][0]["message_id"]
    assert answer["evidence_chain"][0]["permission_state"]["status"] == "authorized"


def test_answer_packet_insufficient_evidence(tmp_path: Path) -> None:
    index_path, graph_path = _build(tmp_path)
    packet = query_graph_packet(index_path, graph_path, "Galaxy S99 unicorn modem volte")
    answer = render_answer_packet(packet)
    assert answer["answer_report"]["answer_status"] == "insufficient_evidence"
    assert answer["warning_report"]["status"] == "insufficient_evidence"
