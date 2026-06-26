# AOA-TELEGRAM-D-0001: Permissioned Conversation Proof

Status: accepted

Telegram is modeled as a permissioned conversation source. The first public repo
proof uses synthetic data and separates Bot API coverage from TDLib/user-session
and takeout/export coverage.

Consequences:

- Bot API is not treated as account-wide Telegram access.
- DMs require connected-account or export mode.
- `permission_state` is part of the evidence contract.
- Heavy and sensitive data stays outside Git.
