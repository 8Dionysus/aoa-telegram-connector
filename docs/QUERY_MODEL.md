# Query Model

Queries run over the local message index. They do not call Telegram search.

The evidence packet includes:

- query terms
- source mode
- conversation id
- message id
- source URL or local source ref
- permission state
- freshness state
- graph context when available
