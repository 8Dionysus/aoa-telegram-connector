# Permissioned Conversation Contract

Telegram and Discord connectors share a conversation-first contract.

Core records:

- `conversation`
- `message`
- `author`
- `permission_state`
- `freshness_state`
- `source_ref`
- `evidence_packet`
- `answer_packet`

The contract preserves older connector-family concepts such as `warning_report`
and `freshness_report`, but does not require every chat message to become a
formal claim. Message graph relations may support later `claim_relation`
extraction.

Required answer statuses:

- `answered`
- `insufficient_permission`
- `insufficient_evidence`

Required semantics:

- DMs and private groups are account-local, explicit-scope data.
- Edits and deletes are graph/freshness facts, not overwritten history.
- Attachment metadata may be indexed; attachment download is forbidden by
  default.
- `permission_state` is part of evidence, not an operational side note.
