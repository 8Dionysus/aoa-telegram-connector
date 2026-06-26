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

## Access Modes

- `bot_api`: channel/group messages visible to the configured bot.
- `tdlib_user_session`: operator-local connected account mode for authorized
  chats, groups, channels, and DMs.
- `takeout_export`: offline import of connected-account export/takeout data.

The connector does not own Telegram credentials or sessions. Any live TDLib
runtime must keep secrets outside Git and report permission state explicitly.

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
