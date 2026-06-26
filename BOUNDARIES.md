# Boundaries

This connector may model Telegram messages only through explicit authorized
source modes. It must not pretend Bot API has account-wide DM visibility.

Allowed starter data is synthetic. Real local data must stay under configured
storage roots and out of Git.

`insufficient_permission` is a successful boundary result when the requested
chat, group, DM, or history is outside the configured scope.
