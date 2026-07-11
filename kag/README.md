# aoa-telegram-connector Local KAG Provider

`kag/` exposes the current Telegram connector provider packet as portable
source-linked records.

## Operating Card

| Field | Route |
| --- | --- |
| role | local KAG provider for Telegram connector policy, permission boundary, storage boundary, and runtime contract handles |
| records | `nodes/`, `edges/`, `indexes/`, `projections/`, `receipts/` |
| manifest | `manifest.json` |
| source route | `connector/README.md`, `connector/SOURCE_POLICY.md`, `connector/STORAGE_POLICY.md` |
| consumer route | `aoa-kag` registry/composition, `abyss-stack`, MCP resources |
| owner return | `BOUNDARIES.md` |

## Record Classes

| Class | Current record |
| --- | --- |
| node | source surface and permission/storage boundary |
| edge | source surface routes to the permission, storage, and runtime boundary |
| index | repository source, entity, artifact, and event indexes |
| projection | MCP-readable source-return packet |
| receipt | validation receipt for the current owner route |

Git holds compact provider records and source-return handles. Runtime serving
state and generated connector payloads stay with their owning storage routes.
