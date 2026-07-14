from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path

from aoa_telegram_connector.normalize import normalize_snapshot


REPO_ROOT = Path(__file__).resolve().parents[2]
FIXTURE_PATH = (
    REPO_ROOT / "connector" / "fixtures" / "telegram" / "starter_conversation.json"
)
PORT_PATH = REPO_ROOT / "stats" / "port.manifest.json"
PACKET_PATHS = {
    "bot_api": REPO_ROOT
    / "stats"
    / "packets"
    / "starter-message-authorized-observability-ratio.bot-api.reference.json",
    "tdlib_user_session": REPO_ROOT
    / "stats"
    / "packets"
    / "starter-message-authorized-observability-ratio.tdlib-user-session.reference.json",
}
PAIRED_MODES = ("bot_api", "tdlib_user_session")


def load_json(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def normalized_fixture(tmp_path: Path, mode: str) -> dict[str, object]:
    path = normalize_snapshot(
        FIXTURE_PATH,
        "telegram:fixture",
        tmp_path / mode,
        mode=mode,
    )
    return load_json(path)


def normalized_pair(tmp_path: Path) -> dict[str, dict[str, object]]:
    return {mode: normalized_fixture(tmp_path, mode) for mode in PAIRED_MODES}


def derive_authorized_observability_ratio(
    fixture: object,
    normalized_by_mode: object,
    mode: str,
) -> dict[str, object]:
    if mode not in PAIRED_MODES:
        return {"status": "unknown", "reason": "unsupported_permission_posture"}
    if (
        not isinstance(normalized_by_mode, dict)
        or set(normalized_by_mode) != set(PAIRED_MODES)
    ):
        return {"status": "unknown", "reason": "unpaired_normalized_outputs"}
    if (
        not isinstance(fixture, dict)
        or fixture.get("schema") != "aoa_telegram_fixture_snapshot_v1"
    ):
        return {"status": "unknown", "reason": "malformed_fixture"}
    conversations = fixture.get("conversations")
    if not isinstance(conversations, list):
        return {"status": "unknown", "reason": "malformed_fixture"}

    expected: dict[tuple[str, str], dict[str, object]] = {}
    for conversation in conversations:
        if not isinstance(conversation, dict):
            return {"status": "unknown", "reason": "malformed_fixture_conversation"}
        conversation_id = conversation.get("conversation_id")
        conversation_type = conversation.get("conversation_type")
        allowed_modes = conversation.get("allowed_modes")
        messages = conversation.get("messages")
        if (
            not isinstance(conversation_id, str)
            or not conversation_id
            or not isinstance(conversation_type, str)
            or not conversation_type
            or not isinstance(allowed_modes, list)
            or any(not isinstance(item, str) for item in allowed_modes)
            or not isinstance(messages, list)
        ):
            return {"status": "unknown", "reason": "malformed_fixture_conversation"}
        for message in messages:
            if not isinstance(message, dict):
                return {"status": "unknown", "reason": "malformed_fixture_message"}
            message_id = message.get("message_id")
            text = message.get("text")
            visible_modes = message.get("visible_in_modes")
            if (
                not isinstance(message_id, str)
                or not message_id
                or not isinstance(text, str)
                or not text.strip()
                or not isinstance(visible_modes, list)
                or any(not isinstance(item, str) for item in visible_modes)
            ):
                return {"status": "unknown", "reason": "malformed_fixture_message"}
            paired_visibility = set(visible_modes).intersection(PAIRED_MODES)
            if not paired_visibility:
                continue
            if not paired_visibility.issubset(set(allowed_modes)):
                return {
                    "status": "unknown",
                    "reason": "contradictory_fixture_permission_envelope",
                }
            identity = (conversation_id, message_id)
            if identity in expected:
                return {
                    "status": "unknown",
                    "reason": "duplicate_fixture_message_identity",
                }
            expected[identity] = {
                "visible_modes": paired_visibility,
                "conversation_type": conversation_type,
                "sensitivity": message.get(
                    "sensitivity", "public_or_channel_visible"
                ),
            }
    if not expected:
        return {"status": "unknown", "reason": "empty_paired_message_population"}

    normalized = normalized_by_mode[mode]
    if (
        not isinstance(normalized, dict)
        or normalized.get("schema") != "aoa_telegram_normalized_snapshot_v1"
    ):
        return {"status": "unknown", "reason": "malformed_normalized_snapshot"}
    normalized_conversations = normalized.get("conversations")
    if not isinstance(normalized_conversations, list):
        return {"status": "unknown", "reason": "malformed_normalized_snapshot"}

    materialized: dict[tuple[str, str], dict[str, object]] = {}
    for conversation in normalized_conversations:
        if not isinstance(conversation, dict):
            return {
                "status": "unknown",
                "reason": "malformed_normalized_conversation",
            }
        authorization = conversation.get("authorization_state")
        messages = conversation.get("messages")
        if (
            not isinstance(authorization, dict)
            or authorization.get("mode") != mode
            or authorization.get("authorized") is not True
            or authorization.get("permission_state") != "authorized"
            or not isinstance(messages, list)
        ):
            return {
                "status": "unknown",
                "reason": "contradictory_normalized_authorization",
            }
        for message in messages:
            if not isinstance(message, dict):
                return {"status": "unknown", "reason": "malformed_normalized_message"}
            conversation_id = message.get("conversation_id")
            message_id = message.get("message_id")
            if (
                not isinstance(conversation_id, str)
                or not isinstance(message_id, str)
                or not conversation_id
                or not message_id
            ):
                return {"status": "unknown", "reason": "malformed_normalized_identity"}
            identity = (conversation_id, message_id)
            if identity in materialized:
                return {
                    "status": "unknown",
                    "reason": "duplicate_normalized_message_identity",
                }
            if identity not in expected:
                return {
                    "status": "unknown",
                    "reason": "unexpected_normalized_message_identity",
                }
            source = expected[identity]
            if mode not in source["visible_modes"]:
                return {
                    "status": "unknown",
                    "reason": "normalized_message_outside_mode_visibility",
                }
            permission = message.get("permission_state")
            private = source["sensitivity"] in {"private_dm", "closed_group"}
            expected_reason = (
                "connected_account_scope" if private else "configured_allowlist"
            )
            if (
                message.get("schema") != "aoa_telegram_normalized_message_v1"
                or message.get("source_mode") != mode
                or message.get("conversation_type") != source["conversation_type"]
                or message.get("sensitivity") != source["sensitivity"]
                or not isinstance(message.get("text"), str)
                or not str(message["text"]).strip()
                or not isinstance(permission, dict)
                or permission.get("status") != "authorized"
                or permission.get("mode") != mode
                or permission.get("requires_operator_local_session") is not private
                or permission.get("reason") != expected_reason
            ):
                return {
                    "status": "unknown",
                    "reason": "contradictory_normalized_permission_state",
                }
            materialized[identity] = message

    numerator = len(materialized)
    denominator = len(expected)
    return {
        "status": "observed",
        "numerator": numerator,
        "denominator": denominator,
        "ratio": numerator / denominator,
        "source_mode": mode,
    }


def test_reference_packets_match_current_paired_permission_outputs(
    tmp_path: Path,
) -> None:
    fixture = load_json(FIXTURE_PATH)
    outputs = normalized_pair(tmp_path)
    expected = {
        "bot_api": (2, 3, 2 / 3),
        "tdlib_user_session": (3, 3, 1.0),
    }

    for mode, (numerator, denominator, ratio) in expected.items():
        derived = derive_authorized_observability_ratio(fixture, outputs, mode)
        packet = load_json(PACKET_PATHS[mode])

        assert derived == {
            "status": "observed",
            "numerator": numerator,
            "denominator": denominator,
            "ratio": ratio,
            "source_mode": mode,
        }
        assert packet["population"]["size"] == denominator
        assert packet["sample"]["size"] == denominator
        assert packet["dimensions"] == {"source_mode": mode}
        assert packet["value"] == {
            "status": "observed",
            "kind": "ratio",
            "unit": "1",
            "number": ratio,
            "numerator": numerator,
            "denominator": denominator,
        }
        assert packet["progress"] == {
            "state": "terminal",
            "completed": 3,
            "total": 3,
        }


def test_missing_mode_visible_message_is_an_observed_gap(tmp_path: Path) -> None:
    fixture = load_json(FIXTURE_PATH)
    outputs = normalized_pair(tmp_path)
    outputs["tdlib_user_session"]["conversations"][0]["messages"].pop()

    assert derive_authorized_observability_ratio(
        fixture,
        outputs,
        "tdlib_user_session",
    ) == {
        "status": "observed",
        "numerator": 2,
        "denominator": 3,
        "ratio": 2 / 3,
        "source_mode": "tdlib_user_session",
    }


def test_valid_empty_normalized_collection_is_observed_zero(tmp_path: Path) -> None:
    outputs = normalized_pair(tmp_path)
    outputs["tdlib_user_session"]["conversations"] = []

    derived = derive_authorized_observability_ratio(
        load_json(FIXTURE_PATH),
        outputs,
        "tdlib_user_session",
    )

    assert derived == {
        "status": "observed",
        "numerator": 0,
        "denominator": 3,
        "ratio": 0.0,
        "source_mode": "tdlib_user_session",
    }


def test_malformed_duplicate_unexpected_contradictory_and_unpaired_are_unknown(
    tmp_path: Path,
) -> None:
    fixture = load_json(FIXTURE_PATH)
    outputs = normalized_pair(tmp_path)

    duplicate_source = deepcopy(fixture)
    duplicate_source["conversations"][0]["messages"].append(
        deepcopy(duplicate_source["conversations"][0]["messages"][0])
    )
    empty_source = deepcopy(fixture)
    empty_source["conversations"] = []
    duplicate_normalized = deepcopy(outputs)
    duplicate_normalized["tdlib_user_session"]["conversations"][0][
        "messages"
    ].append(
        deepcopy(
            duplicate_normalized["tdlib_user_session"]["conversations"][0][
                "messages"
            ][0]
        )
    )
    unexpected = deepcopy(outputs)
    unexpected["bot_api"]["conversations"][0]["messages"][0][
        "message_id"
    ] = "unexpected"
    contradictory = deepcopy(outputs)
    contradictory["tdlib_user_session"]["conversations"][1]["messages"][0][
        "permission_state"
    ]["requires_operator_local_session"] = False
    outside_visibility = deepcopy(outputs)
    private_message = deepcopy(
        outside_visibility["tdlib_user_session"]["conversations"][1]["messages"][0]
    )
    private_message["source_mode"] = "bot_api"
    private_message["permission_state"]["mode"] = "bot_api"
    outside_visibility["bot_api"]["conversations"][0]["messages"].append(
        private_message
    )
    wrong_mode = deepcopy(outputs)
    wrong_mode["bot_api"]["conversations"][0]["messages"][0][
        "source_mode"
    ] = "tdlib_user_session"

    cases = (
        derive_authorized_observability_ratio(None, outputs, "bot_api"),
        derive_authorized_observability_ratio(
            fixture,
            {"bot_api": outputs["bot_api"]},
            "bot_api",
        ),
        derive_authorized_observability_ratio(
            duplicate_source,
            outputs,
            "tdlib_user_session",
        ),
        derive_authorized_observability_ratio(
            empty_source,
            outputs,
            "tdlib_user_session",
        ),
        derive_authorized_observability_ratio(
            fixture,
            duplicate_normalized,
            "tdlib_user_session",
        ),
        derive_authorized_observability_ratio(fixture, unexpected, "bot_api"),
        derive_authorized_observability_ratio(
            fixture,
            contradictory,
            "tdlib_user_session",
        ),
        derive_authorized_observability_ratio(
            fixture,
            outside_visibility,
            "bot_api",
        ),
        derive_authorized_observability_ratio(fixture, wrong_mode, "bot_api"),
        derive_authorized_observability_ratio(
            fixture,
            outputs,
            "mtproto_user_session",
        ),
        derive_authorized_observability_ratio(
            fixture,
            {**outputs, "bot_api": {"schema": "wrong"}},
            "bot_api",
        ),
    )

    assert all(case["status"] == "unknown" for case in cases)


def test_measurement_stays_reference_only_and_below_permission_eval_and_runtime_authority() -> None:
    port = load_json(PORT_PATH)
    measurement = port["measurements"][0]
    ceiling = measurement["authority_ceiling"]

    assert port["evidence_posture"] == {
        "live_state": "reference_only",
        "privacy": "public",
        "raw_content_allowed": False,
    }
    assert measurement["live_state"] == {"capability": "reference_only"}
    assert measurement["aggregation"] == {"operator": "none", "across": []}
    assert measurement["dimensions"]["allowed"] == [
        {"name": "source_mode", "max_cardinality": 2, "sensitivity": "public"}
    ]
    assert "real bot or connected-account authorization" in ceiling
    assert "connector readiness" in ceiling
    assert "eval success" in ceiling
    for path in PACKET_PATHS.values():
        packet = load_json(path)
        packet_text = json.dumps(packet)
        assert packet["posture"]["raw_content_included"] is False
        assert "vendor_boot" not in packet_text
        assert "tg:dm:self-notes" not in packet_text
