from pathlib import Path

from aoa_telegram_connector.normalize import normalize_snapshot
from aoa_telegram_connector.policy.rules import route_decision


FIXTURE = Path("connector/fixtures/telegram/starter_conversation.json")


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
    assert route_decision("telegram:takeout_export:account:self")["operator_local"] is True
    assert route_decision("telegram:bot_api:private_dm:user")["allowed"] is False
    assert route_decision("telegram:write:send_message")["allowed"] is False
    assert route_decision("telegram:download:attachment")["allowed"] is False
