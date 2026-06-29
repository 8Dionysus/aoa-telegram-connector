# Agent Install Route

1. Read `AGENTS.md`, `BOUNDARIES.md`, and `connector/SOURCE_POLICY.md`.
2. Run `python scripts/validate_connector.py`.
3. Run `PYTHONPATH=src python -m pytest -q`.
4. Run the no-network starter proof.
5. Configure external roots before real Telegram data.
6. For the first real pilot, prefer `materialize telegram-desktop-export`
   against an operator-selected Telegram Desktop `result.json`.
7. For the API pilot, use `materialize mtproto-history` with
   `TELEGRAM_API_ID` and `TELEGRAM_API_HASH` supplied by local vault/env state.
8. For the owned-source base, use `sources add`, `sources plan-sync`, and
   `sources sync` to ingest explicit channels, groups, paid_member sources,
   private chats, and Saved Messages visible to the connected account.
9. Never place Telegram tokens, TDLib sessions, MTProto sessions, API hashes,
   takeout exports, or private
   messages in Git.
