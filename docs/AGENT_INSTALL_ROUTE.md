# Agent Install Route

1. Read `AGENTS.md`, `BOUNDARIES.md`, and `connector/SOURCE_POLICY.md`.
2. Run `python scripts/validate_connector.py`.
3. Run `PYTHONPATH=src python -m pytest -q`.
4. Run the no-network starter proof.
5. Configure external roots before real Telegram data.
6. Never place Telegram tokens, TDLib sessions, takeout exports, or private
   messages in Git.
