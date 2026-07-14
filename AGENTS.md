# AGENTS.md

Root route card for `aoa-telegram-connector`.

## Purpose

This repository owns the Telegram side of the permissioned conversation
connector family: source policy, starter schemas, synthetic fixtures,
normalization, local search, graph packets, answer packets, local evals, and
bounded owner-local statistics over connector evidence.

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
- Shared statistical grammar and cross-owner composition belong to
  `aoa-stats`; local stats cannot claim permission, eval, readiness, runtime,
  or live-source authority.

## Read Before Editing

1. `CHARTER.md`, `BOUNDARIES.md`, and the relevant design document under
   `docs/`.
2. `connector/SOURCE_POLICY.md` and `connector/STORAGE_POLICY.md` for source or
   storage changes.
3. The nearest nested `AGENTS.md` for `.connector-state/`, `evals/`, `kag/`, or
   `stats/`.
4. The executable owner: CLI parser and implementation, validator, test, or CI
   workflow relevant to the change.

## Validation

Run from the repository root:

```bash
python scripts/validate_connector.py
PYTHONPATH=src python -m pytest -q
PYTHONPATH=src python -m aoa_telegram_connector.cli doctor
PYTHONPATH=src python -m aoa_telegram_connector.cli policy check
PYTHONPATH=src python -m aoa_telegram_connector.cli eval permissions
PYTHONPATH=src python -m aoa_telegram_connector.cli eval answer-packets
AOA_STATS_ROOT=/path/to/aoa-stats python scripts/validate_local_stats_port.py
```

The CI workflow owns the exhaustive repository route. Ordinary Markdown
explains behavior and links to executable owners rather than duplicating
command catalogs.
