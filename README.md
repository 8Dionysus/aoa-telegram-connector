# aoa-telegram-connector

`aoa-telegram-connector` is a GitHub-publishable AoA connector skeleton for
permissioned Telegram conversation evidence.

It proves a small no-network path from the synthetic fixture through
permission-aware normalization, local index and graph construction, evidence
query, answer packets, and local evals. The bounded operator route is owned by
`AGENTS.md`; exact behavior and syntax remain with the CLI parser, validator,
tests, and CI workflow.

It also supports an operator-selected Telegram Desktop JSON export pilot whose
generated raw, normalized, index, graph, and answer artifacts remain under the
configured storage roots.

The connected-account API pilot uses the optional API dependency and receives
Telegram credentials only from operator-local environment or vault state.

For a real operator-owned source base, register the sources your connected
account can legitimately see, inspect the read-only sync plan, and only then
materialize a bounded run through the CLI-owned source route.

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

## Local statistics

The root `stats/` port compares the authorized normalized share of the same
three-message public synthetic starter population under `bot_api` and
`tdlib_user_session`. It exports only reference counts and source links;
permission policy, message content, eval verdicts, and live state stay with
their owners. See `stats/README.md` for the measurement boundary.
