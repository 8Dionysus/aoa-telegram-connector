# Runtime Contract

This repo exposes connector logic. Runtime/MCP deployment belongs in
`abyss-stack`.

Future stack service name:

```text
aoa-telegram-connector-mcp
```

The MCP wrapper must stay read-only and stdio-first. It should call this repo's
CLI/API and return the connector JSON packets without owning Telegram ingest
logic.

Required packet fields:

- `agent_answer`
- `evidence_chain`
- `permission_report`
- `conflict_report`
- `freshness_report`
- `applicability_report`
- `warning_report`
- `network_touched=false` for local query/answer paths
- `read_only=true` for local query/answer paths
- `internal-search source route` must remain local-only; Telegram internal
  search is not a corpus source

If a requested scope is outside the configured allowlist, return
`insufficient_permission`. If the local base lacks evidence, return
`insufficient_evidence`.
