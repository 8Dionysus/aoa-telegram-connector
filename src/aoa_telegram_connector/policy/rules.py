"""Telegram source-route policy helpers."""

from __future__ import annotations


ALLOWED_PREFIXES = (
    "telegram:bot_api:channel:",
    "telegram:bot_api:group:",
    "telegram:tdlib_user_session:",
    "telegram:mtproto_user_session:",
    "telegram:takeout_export:",
)

DENIED_MARKERS = ("write:", "send_message", "download:", "attachment", "private_dm")


def route_decision(route: str) -> dict[str, object]:
    lowered = route.casefold()
    if lowered.startswith("telegram:bot_api:private_dm"):
        return _deny(route, "bot_api_cannot_collect_connected_account_dm")
    if any(marker in lowered for marker in DENIED_MARKERS):
        return _deny(route, "forbidden_write_or_download_route")
    if route.startswith(ALLOWED_PREFIXES):
        mode = route.split(":", 2)[1]
        return {
            "route": route,
            "allowed": True,
            "mode": mode,
            "requires_explicit_allowlist": True,
            "operator_local": mode in {"tdlib_user_session", "mtproto_user_session", "takeout_export"},
            "reason": "authorized_telegram_source_mode",
        }
    return _deny(route, "unknown_or_unconfigured_telegram_route")


def _deny(route: str, reason: str) -> dict[str, object]:
    return {"route": route, "allowed": False, "reason": reason}
