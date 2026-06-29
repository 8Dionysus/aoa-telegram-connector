import json
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace

from aoa_telegram_connector.normalize import normalize_snapshot
from aoa_telegram_connector.parse.mtproto_history import mtproto_message_to_snapshot_message
from aoa_telegram_connector.parse.telegram_desktop_export import load_telegram_desktop_export
from aoa_telegram_connector.policy.rules import route_decision
from aoa_telegram_connector.sources import build_sync_plan, load_registry, select_sources, upsert_source


FIXTURE = Path("connector/fixtures/telegram/starter_conversation.json")
DESKTOP_EXPORT = Path("connector/fixtures/telegram/telegram_desktop_export_result.json")


def test_normalizer_keeps_bot_visible_channel_scope(tmp_path: Path) -> None:
    output = normalize_snapshot(FIXTURE, "telegram:fixture", tmp_path, mode="bot_api")
    text = output.read_text(encoding="utf-8")
    assert "aoa_telegram_normalized_conversation_v1" in text
    assert "public_channel" in text
    assert "private_dm" not in text
    assert "vendor_boot.img" in text


def test_normalizer_user_session_includes_connected_account_dm(tmp_path: Path) -> None:
    output = normalize_snapshot(FIXTURE, "telegram:fixture", tmp_path, mode="tdlib_user_session")
    text = output.read_text(encoding="utf-8")
    assert "private_dm" in text
    assert "requires_operator_local_session" in text
    assert "Bot API must not collect personal DMs" in text


def test_policy_models_authorized_and_denied_routes() -> None:
    assert route_decision("telegram:bot_api:channel:@aoa_android_lab")["allowed"] is True
    assert route_decision("telegram:tdlib_user_session:dm:self")["operator_local"] is True
    assert route_decision("telegram:mtproto_user_session:channel:@aoa_android_lab")["operator_local"] is True
    assert route_decision("telegram:takeout_export:account:self")["operator_local"] is True
    assert route_decision("telegram:bot_api:private_dm:user")["allowed"] is False
    assert route_decision("telegram:write:send_message")["allowed"] is False
    assert route_decision("telegram:download:attachment")["allowed"] is False


def test_telegram_desktop_export_parser_keeps_text_and_attachment_metadata() -> None:
    snapshot = load_telegram_desktop_export(DESKTOP_EXPORT)
    conversation = snapshot["conversations"][0]
    assert conversation["allowed_modes"] == ["takeout_export"]
    assert conversation["conversation_type"] == "public_channel"
    messages = conversation["messages"]
    assert messages[1]["reply_to_message_id"] == "11"
    assert "vendor_boot.img" in messages[1]["text"]
    assert messages[1]["attachments_metadata"][0]["downloaded"] is False


def test_telegram_desktop_export_normalizes_as_takeout_export(tmp_path: Path) -> None:
    snapshot = load_telegram_desktop_export(DESKTOP_EXPORT)
    raw = tmp_path / "raw.json"
    raw.write_text(json.dumps(snapshot), encoding="utf-8")
    output = normalize_snapshot(raw, "telegram:desktop-export", tmp_path / "normalized", mode="takeout_export")
    text = output.read_text(encoding="utf-8")
    assert "aoa_telegram_normalized_conversation_v1" in text
    assert "takeout_export" in text
    assert "vendor_boot.img" in text


def test_mtproto_message_converter_preserves_readable_text_and_media_metadata() -> None:
    message = SimpleNamespace(
        id=42,
        raw_text="Warning: vendor_boot.img mismatch can bootloop Xiaomi 13T #hyperos",
        date=datetime(2026, 6, 10, 12, 0, tzinfo=UTC),
        edit_date=None,
        reply_to_msg_id=41,
        sender_id=777,
        entities=[],
        media=object(),
        file=SimpleNamespace(name="warning.webp", mime_type="image/webp", size=1234),
    )
    converted = mtproto_message_to_snapshot_message(message)
    assert converted is not None
    assert converted["message_id"] == "42"
    assert converted["posted_at"] == "2026-06-10T12:00:00Z"
    assert converted["reply_to_message_id"] == "41"
    assert converted["visible_in_modes"] == ["mtproto_user_session"]
    assert converted["attachments_metadata"][0]["downloaded"] is False
    assert converted["source_receipt"]["adapter"] == "telethon.iter_messages"


def test_source_registry_models_owned_public_paid_private_and_saved_sources(tmp_path: Path) -> None:
    channel, _, _ = upsert_source(tmp_path, source_ref="@aoa_ai_radar", kind="channel", access="public", tags=["ai", "agents"], trust_score=0.8)
    paid, _, _ = upsert_source(tmp_path, source_ref="t.me/+paid-lab", kind="paid_group", tags=["android"])
    saved, _, _ = upsert_source(tmp_path, source_ref="me", kind="saved_messages", tags=["self"])

    assert channel["conversation_type"] == "public_channel"
    assert paid["access"] == "paid_member"
    assert saved["access"] == "self_saved"
    registry = load_registry(tmp_path)
    selected = select_sources(registry, tags=["ai"])
    assert [source["source_ref"] for source in selected] == ["@aoa_ai_radar"]

    plan = build_sync_plan(run_id="pytest-owned", sources=select_sources(registry), limit=50)
    assert plan["selected_count"] == 3
    assert plan["download_touched"] is False
    assert all(step["include_media"] == "none" for step in plan["steps"])
