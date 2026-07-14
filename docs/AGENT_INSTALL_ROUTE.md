# Agent Install Route

1. Read `AGENTS.md`, `BOUNDARIES.md`, and `connector/SOURCE_POLICY.md`.
2. Follow the bounded operator route in `AGENTS.md`; the validator, tests, CLI
   parser, and CI workflow remain the executable owners.
3. Confirm the no-network starter proof before considering connected data.
4. Configure external roots before real Telegram data.
5. Prefer the Telegram Desktop export adapter for the first no-secret real
   pilot and keep its result under operator-selected storage.
6. Supply API credentials only from local vault or environment state for the
   connected-account pilot.
7. Build an owned-source base only from explicit public, paid-member, private,
   and Saved Messages sources visible to the connected account.
8. Never place Telegram tokens, TDLib sessions, MTProto sessions, API hashes,
   takeout exports, or private
   messages in Git.
