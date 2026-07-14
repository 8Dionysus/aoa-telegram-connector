# AGENTS.md

Route card for owner-local statistical questions in
`aoa-telegram-connector`. Read the root `AGENTS.md` first.

## Applies To

Everything under `stats/`.

## Role

This directory owns bounded statistics over Telegram connector evidence.
Shared measurement grammar and cross-owner composition remain owned by
`aoa-stats`; permission policy and connector behavior remain owned by this
repository, eval verdicts remain owned by `aoa-evals`, and private or live
Telegram data remains outside Git in configured storage.

## Read Before Editing

1. Root `AGENTS.md`, `CHARTER.md`, and `BOUNDARIES.md`.
2. `connector/SOURCE_POLICY.md` and `connector/STORAGE_POLICY.md`.
3. The starter fixture, normalizer, and permission policy relevant to the
   measure.
4. `evals/AGENTS.md` when the same evidence is also consumed by an eval.
5. `stats/README.md`, `stats/port.manifest.json`, and the central contracts
   under `aoa-stats/stats/`.

## Boundaries

- The reference population is the non-empty set of unique, non-empty-text
  messages in the canonical public synthetic fixture declared visible in at
  least one of the paired `bot_api` and `tdlib_user_session` modes.
- A message enters a mode's numerator only when the normalizer emits the same
  identity with authorized, non-empty text and permission state consistent
  with that declared mode visibility.
- A fixture message that is legitimately invisible to one mode is an observed
  absence, not a materialization failure or eval verdict. This is why the Bot
  API reference ratio is `2 / 3`.
- A missing normalized message declared visible in the selected mode is an
  observed gap. A valid empty normalized collection is an observed zero.
- Malformed, empty, duplicate, unexpected, contradictory, or unpaired source
  and normalized populations are unknown.
- The committed private-DM record is synthetic public test data. Packets must
  not carry message bodies, conversation or message identities, authors, chat
  references, or operator-local state.
- The reference packets are weaker than the fixture, normalizer, permission
  policy, executable audits, eval results, and live Telegram evidence.
- The ratio does not prove live authorization, source coverage, connector
  readiness, retrieval or answer quality, eval success, or runtime health.

## Validation

Inspect the fixture, both normalized mode outputs, and packets first. The port
validator requires a compatible `aoa-stats` checkout through `AOA_STATS_ROOT`,
`.deps/aoa-stats`, or the workspace sibling route. Then run:

```bash
AOA_STATS_ROOT=/path/to/aoa-stats python scripts/validate_local_stats_port.py
PYTHONPATH=src python -m pytest -q tests/unit/test_local_stats_port.py
```

Use the root route for repository-wide validation.

## Closeout

Report both mode-specific ratios, the manual positive and negative cases,
unknown handling, packet posture, central validation, and repository
validation.
