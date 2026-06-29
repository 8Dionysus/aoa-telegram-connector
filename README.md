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

It also supports an operator-selected Telegram Desktop JSON export pilot:

```bash
PYTHONPATH=src python -m aoa_telegram_connector.cli materialize telegram-desktop-export /path/to/result.json --run tg-export-pilot
PYTHONPATH=src python -m aoa_telegram_connector.cli build-index --run tg-export-pilot
PYTHONPATH=src python -m aoa_telegram_connector.cli build-graph --run tg-export-pilot
PYTHONPATH=src python -m aoa_telegram_connector.cli answer "your question" --run tg-export-pilot
```

For the connected-account API pilot, install the optional API extra and provide
Telegram API credentials through local env/vault state:

```bash
PYTHONPATH=src python -m aoa_telegram_connector.cli materialize mtproto-history @channel_or_chat --run tg-api-pilot --limit 200
PYTHONPATH=src python -m aoa_telegram_connector.cli build-index --run tg-api-pilot
PYTHONPATH=src python -m aoa_telegram_connector.cli build-graph --run tg-api-pilot
PYTHONPATH=src python -m aoa_telegram_connector.cli answer "your question" --run tg-api-pilot
```

For a real operator-owned source base, register the sources your connected
account can legitimately see, plan the sync, then sync into one run:

```bash
PYTHONPATH=src python -m aoa_telegram_connector.cli sources add @some_channel --kind channel --access public --tags ai,agents
PYTHONPATH=src python -m aoa_telegram_connector.cli sources add t.me/+paid-lab --kind paid_group --tags android,firmware
PYTHONPATH=src python -m aoa_telegram_connector.cli sources add me --kind saved_messages --tags self,notes --trust-score 1.0
PYTHONPATH=src python -m aoa_telegram_connector.cli sources plan-sync --run tg-owned-sources --limit 500
PYTHONPATH=src python -m aoa_telegram_connector.cli sources sync --run tg-owned-sources --limit 500
PYTHONPATH=src python -m aoa_telegram_connector.cli build-index --run tg-owned-sources
PYTHONPATH=src python -m aoa_telegram_connector.cli build-graph --run tg-owned-sources
PYTHONPATH=src python -m aoa_telegram_connector.cli answer "your question" --run tg-owned-sources
```

The source registry is operator-local generated state under
`CONNECTOR_DATA_ROOT`; it is not committed to Git. Supported source kinds are
`channel`, `group`, `supergroup`, `paid_channel`, `paid_group`, `private_chat`,
and `saved_messages`.

## Modes

| Mode | Coverage | Boundary |
| --- | --- | --- |
| `bot_api` | bot-visible channels/groups | group privacy mode and bot rights limit coverage |
| `mtproto_user_session` | connected-account API history for explicit chat/channel allowlists | operator-local, bounded, read-only, no downloads |
| `tdlib_user_session` | connected-account chats/channels/groups/DMs | operator-local, sensitive, never default for public clones |
| `takeout_export` | offline connected-account archive | import-only backfill; no live session required |

The repository stores method, code, schemas, synthetic fixtures, evals, and
docs. It does not store real Telegram sessions, tokens, private messages, raw
exports, indexes, vectors, graph databases, or media downloads.
