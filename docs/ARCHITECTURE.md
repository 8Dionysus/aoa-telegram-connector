# Architecture

`aoa-telegram-connector` turns authorized Telegram conversation snapshots into
local evidence packets.

```text
fixture/export/session snapshot
  -> normalize conversations/messages
  -> build local keyword index
  -> build conversation graph
  -> query evidence packet
  -> answer packet
```

For operator-owned Telegram sources the live route is:

```text
operator-local source registry
  -> MTProto connected-account sync plan
  -> bounded read-only source sync
  -> raw event snapshot with source_receipt
  -> normalize conversations/messages
  -> build local index and graph
  -> answer/digest packet
```

## Access Modes

- `bot_api`: channel/group messages visible to the configured bot.
- `tdlib_user_session`: operator-local connected account mode for authorized
  chats, groups, channels, and DMs.
- `mtproto_user_session`: operator-local connected account API mode for
  explicit source registry entries including public channels/groups,
  paid_member sources, private chats, and Saved Messages.
- `takeout_export`: offline import of connected-account export/takeout data.

The connector does not own Telegram credentials or sessions. Any live TDLib
runtime must keep secrets outside Git and report permission state explicitly.

## Source Registry

The source registry lives in `CONNECTOR_DATA_ROOT`, not in Git. It describes
operator-selected sources with `source_ref`, `kind`, `access`, tags, trust score,
conversation id, and media policy. `paid_member`, `private_authorized`, and
`self_saved` entries are legitimate connected-account scopes, not public seed
data.

The current sync implementation indexes text and attachment metadata only.
`include_media=none` is the live default and the only implemented sync policy;
future media policies must keep downloads explicit and receipt-backed.

## Graph

Starter edges include:

- `conversation_contains_message`
- `message_authored_by`
- `message_replies_to_message`
- `message_edits_prior_version`
- `message_deleted_tombstone`
- `message_pinned_contextualizes_conversation`
- `message_mentions_entity`
- `message_warns_about_context`
- `message_supersedes_prior_guidance`
