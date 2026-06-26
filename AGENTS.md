# AGENTS.md

Root route card for `aoa-telegram-connector`.

## Purpose

This repository owns the Telegram side of the permissioned conversation
connector family: source policy, starter schemas, synthetic fixtures,
normalization, local search, graph packets, answer packets, and local evals.

It is public method and code, not a Telegram data dump.

## Boundaries

- Do not commit tokens, sessions, phone numbers, 2FA material, user exports,
  private messages, raw corpora, indexes, graph databases, vectors, or caches.
- Bot API mode may collect only bot-visible allowlisted channels/groups.
- TDLib/MTProto and takeout/export are operator-local connected-account modes.
- Closed/private groups require legitimate connected-account access and explicit
  operator scope.
- Attachment downloads and write actions are forbidden by default.
- Runtime/MCP belongs in `abyss-stack`; this repo owns connector logic.

## Validation

Run from the repository root:

```bash
python scripts/validate_connector.py
PYTHONPATH=src python -m pytest -q
PYTHONPATH=src python -m aoa_telegram_connector.cli doctor
PYTHONPATH=src python -m aoa_telegram_connector.cli policy check
PYTHONPATH=src python -m aoa_telegram_connector.cli eval permissions
PYTHONPATH=src python -m aoa_telegram_connector.cli eval answer-packets
```
