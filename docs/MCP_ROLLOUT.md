# MCP Rollout

The connector repo is not the runtime owner.

`abyss-stack` should later expose `aoa-telegram-connector-mcp` as a thin,
read-only, stdio-first wrapper over this repo's JSON packets.

Forbidden MCP behavior:

- storing Telegram sessions
- writing to Telegram
- downloading media by default
- widening scope beyond configured allowlists
