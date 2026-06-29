# Starter Proof

The starter proof is no-network and synthetic.

It demonstrates:

- Bot API mode sees public/channel-visible messages.
- TDLib user-session mode sees the connected-account private DM fixture.
- The graph preserves reply, edit, pin, warning, and supersession context.
- Answer packets distinguish `answered`, `insufficient_permission`, and
  `insufficient_evidence`.

Run:

```bash
PYTHONPATH=src python -m aoa_telegram_connector.cli materialize fixture --mode tdlib_user_session
PYTHONPATH=src python -m aoa_telegram_connector.cli build-index
PYTHONPATH=src python -m aoa_telegram_connector.cli build-graph
PYTHONPATH=src python -m aoa_telegram_connector.cli eval permissions
PYTHONPATH=src python -m aoa_telegram_connector.cli eval answer-packets
```

## Telegram Desktop Export Pilot

For a no-secret real pilot, export a small chat/channel from Telegram Desktop as
machine-readable JSON and import the resulting `result.json`:

```bash
PYTHONPATH=src python -m aoa_telegram_connector.cli materialize telegram-desktop-export /path/to/result.json --run tg-export-pilot
PYTHONPATH=src python -m aoa_telegram_connector.cli build-index --run tg-export-pilot
PYTHONPATH=src python -m aoa_telegram_connector.cli build-graph --run tg-export-pilot
PYTHONPATH=src python -m aoa_telegram_connector.cli query-graph "vendor_boot bootloop warning" --run tg-export-pilot
PYTHONPATH=src python -m aoa_telegram_connector.cli answer "vendor_boot bootloop warning" --run tg-export-pilot
```

The import path is `takeout_export`: it is read-only, no-network, and stores raw
and generated artifacts under the configured connector storage roots.

## MTProto API Pilot

For a connected-account pilot, set `TELEGRAM_API_ID` and `TELEGRAM_API_HASH` in
local vault/env state, then materialize a bounded allowlisted chat:

```bash
PYTHONPATH=src python -m aoa_telegram_connector.cli materialize mtproto-history @channel_or_chat --run tg-api-pilot --limit 200
PYTHONPATH=src python -m aoa_telegram_connector.cli build-index --run tg-api-pilot
PYTHONPATH=src python -m aoa_telegram_connector.cli build-graph --run tg-api-pilot
PYTHONPATH=src python -m aoa_telegram_connector.cli query-graph "vendor_boot bootloop warning" --run tg-api-pilot
PYTHONPATH=src python -m aoa_telegram_connector.cli answer "vendor_boot bootloop warning" --run tg-api-pilot
```

The MTProto path touches the network during materialization only. Query, graph,
answer, and MCP access remain local, read-only, and no-network.

## Owned Source Registry Pilot

For a deeper personal source base, register each source the connected account
can legitimately see. The registry is generated operator-local state under
`CONNECTOR_DATA_ROOT`; do not commit it.

```bash
PYTHONPATH=src python -m aoa_telegram_connector.cli sources add @some_public_channel --kind channel --access public --tags ai,agents
PYTHONPATH=src python -m aoa_telegram_connector.cli sources add t.me/+paid-lab --kind paid_group --tags android,firmware
PYTHONPATH=src python -m aoa_telegram_connector.cli sources add @trusted_person --kind private_chat --access private_authorized --tags dm,work
PYTHONPATH=src python -m aoa_telegram_connector.cli sources add me --kind saved_messages --tags self,notes --trust-score 1.0
PYTHONPATH=src python -m aoa_telegram_connector.cli sources plan-sync --run tg-owned-sources --limit 500
PYTHONPATH=src python -m aoa_telegram_connector.cli sources sync --run tg-owned-sources --limit 500
PYTHONPATH=src python -m aoa_telegram_connector.cli build-index --run tg-owned-sources
PYTHONPATH=src python -m aoa_telegram_connector.cli build-graph --run tg-owned-sources
PYTHONPATH=src python -m aoa_telegram_connector.cli answer "what changed for vendor_boot on Xiaomi 13T" --run tg-owned-sources
```

The live sync currently supports `include_media=none`: text and attachment
metadata are captured, while downloads remain disabled by default.
