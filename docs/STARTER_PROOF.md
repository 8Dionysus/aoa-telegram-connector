# Starter Proof

The starter proof is no-network and synthetic.

It demonstrates:

- Bot API mode sees public/channel-visible messages.
- TDLib user-session mode sees the connected-account private DM fixture.
- The graph preserves reply, edit, pin, warning, and supersession context.
- Answer packets distinguish `answered`, `insufficient_permission`, and
  `insufficient_evidence`.

The exact no-network route is owned by the root `AGENTS.md`, CLI parser,
validator, tests, and CI workflow.

The root `stats/` port records the narrower reference observation that
`bot_api` legitimately materializes `2 / 3` messages from the complete public
synthetic starter population, while `tdlib_user_session` materializes `3 / 3`.
This describes the modeled permission envelope; it is not the permission eval
verdict and does not claim live Telegram coverage.

## Telegram Desktop Export Pilot

For a no-secret real pilot, export a small operator-selected chat or channel as
Telegram Desktop JSON and pass it through the CLI-owned export adapter.

The import path is `takeout_export`: it is read-only, no-network, and stores raw
and generated artifacts under the configured connector storage roots.

## MTProto API Pilot

For a connected-account pilot, supply the Telegram API id and hash from local
vault or environment state, then materialize only a bounded allowlisted chat.

The MTProto path touches the network during materialization only. Query, graph,
answer, and MCP access remain local, read-only, and no-network.

## Owned Source Registry Pilot

For a deeper personal source base, register each source the connected account
can legitimately see. The registry is generated operator-local state under
`CONNECTOR_DATA_ROOT`; do not commit it. Inspect the read-only sync plan before
any bounded network materialization.

The live sync currently supports `include_media=none`: text and attachment
metadata are captured, while downloads remain disabled by default.
