# Telegram Source Policy

This connector is a permissioned conversation connector, not a public forum
crawler.

## Official Surfaces Checked

- Telegram Bot API: `https://core.telegram.org/bots/api`
- Telegram Bot FAQ and privacy mode: `https://core.telegram.org/bots/faq`
- Telegram MTProto methods including `messages.getHistory`,
  `messages.search`, and `channels.getMessages`
- TDLib: `https://core.telegram.org/tdlib`
- Telegram takeout/export API: `https://core.telegram.org/api/takeout`

## Allowed Modes

- `bot_api`: bot-visible channel/group messages from an explicit allowlist.
- `tdlib_user_session`: operator-local connected account mode for chats,
  channels, groups, and private messages the account can legitimately access.
- `takeout_export`: offline connected-account export/backfill mode.
- Closed or private groups only when the connected account has legitimate access
  and the operator explicitly configures that scope.

## Forbidden Routes

- Bot API collection of connected-account private messages.
- Login bypass, hidden APIs, session theft, phone-number capture, 2FA capture,
  or credential storage in Git.
- Write routes: send message, edit, delete, join, invite, react, or reply.
- Attachments download, media download, binary mirrors, firmware pulls, or file
  content ingestion by default. Attachment metadata may be indexed.
- Broad unbounded account scraping.
- Telegram internal search as a crawler source.

## Search Rule

Build local search over authorized snapshots only. If a scope is not authorized,
return `insufficient_permission`. If local evidence is absent, return
`insufficient_evidence`.
