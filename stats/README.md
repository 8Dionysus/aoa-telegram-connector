# aoa-telegram-connector local stats port

This directory exposes statistical questions whose domain meaning belongs to
the Telegram connector. It uses the shared `aoa-stats` grammar without moving
Telegram permission policy, synthetic or private message content, eval
verdicts, or runtime state into the central stats organ.

## Current reference measurement

| Measurement | Source mode | Reference value |
| --- | --- | --- |
| `aoa-telegram-connector/starter-message-authorized-observability-ratio` | `bot_api` | `2 / 3` |
| `aoa-telegram-connector/starter-message-authorized-observability-ratio` | `tdlib_user_session` | `3 / 3` |

The question is: under each paired permission posture in the canonical public
synthetic starter fixture, what fraction of the same declared message
population is materialized as authorized normalized evidence?

The population is a census of the three unique, non-empty-text fixture
messages declared visible in at least one paired mode. It includes two public
channel messages and one synthetic private-DM message. The numerator contains
only matching normalized identities with non-empty text, authorized permission
state, and mode semantics consistent with the fixture. The two observations
are deliberately not aggregated because their difference is the permission
envelope being measured.

The private-DM absence from Bot API output is legitimate and produces the
observed `2 / 3`; it is not an error or eval failure. A missing normalized
message that the fixture declares visible in the selected mode is an observed
gap, and a valid empty output is an observed zero. A malformed, empty,
duplicate, unexpected, contradictory, or mode-unpaired population is unknown.

## Evidence posture

Both packets are public, reference-only snapshots derived from the committed
synthetic fixture and normalizer at source revision
`1ebf5f9074ca014db83ac219ef28c17cbc05c343`. They contain counts and portable
source references, not message text, conversation or message identities,
authors, Telegram source refs, configured storage, live Telegram state, or eval
output. Terminal progress means only that the three-item fixture census was
processed for that mode.

## Authority

The ratio describes modeled authorized observability across two starter source
modes. It does not establish real bot or connected-account authorization, live
channel, group, private-chat, or Saved Messages coverage, source completeness,
index or graph quality, retrieval or answer quality, connector readiness, eval
success, proof verdicts, or runtime health.

## Surfaces

- `port.manifest.json` declares the owner-local question and measurement.
- `packets/` records the two evidence-linked reference observations.
- the public synthetic starter fixture owns the declared message population;
- the normalizer and source policy own visibility and permission semantics;
- `aoa-stats` owns shared validation and cross-owner composition.
