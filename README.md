# aoa-telegram-connector

`aoa-telegram-connector` is a GitHub-publishable AoA connector skeleton for
permissioned Telegram conversation evidence.

It proves a small no-network path:

```bash
python scripts/validate_connector.py
PYTHONPATH=src python -m pytest -q
PYTHONPATH=src python -m aoa_telegram_connector.cli doctor
PYTHONPATH=src python -m aoa_telegram_connector.cli materialize fixture --mode tdlib_user_session
PYTHONPATH=src python -m aoa_telegram_connector.cli build-index
PYTHONPATH=src python -m aoa_telegram_connector.cli build-graph
PYTHONPATH=src python -m aoa_telegram_connector.cli answer "vendor_boot bootloop warning"
```

## Modes

| Mode | Coverage | Boundary |
| --- | --- | --- |
| `bot_api` | bot-visible channels/groups | group privacy mode and bot rights limit coverage |
| `tdlib_user_session` | connected-account chats/channels/groups/DMs | operator-local, sensitive, never default for public clones |
| `takeout_export` | offline connected-account archive | import-only backfill; no live session required |

The repository stores method, code, schemas, synthetic fixtures, evals, and
docs. It does not store real Telegram sessions, tokens, private messages, raw
exports, indexes, vectors, graph databases, or media downloads.
