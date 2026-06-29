# AGENTS.md

## Applies to

This card applies to `aoa-telegram-connector/kag/` and every nested path until a
nearer card narrows the lane.

## Role

`kag/` is the local KAG provider home for `aoa-telegram-connector`.

It exposes compact source-linked records over the Telegram connector policy,
permission boundary, storage boundary, and runtime contract surfaces for
`aoa-kag` registry, composition, and MCP consumers.

## Read before editing

Read the root `AGENTS.md`, `README.md`, `BOUNDARIES.md`,
`connector/README.md`, `connector/SOURCE_POLICY.md`,
`connector/STORAGE_POLICY.md`, `docs/RUNTIME_CONTRACT.md`, and
`kag/manifest.json` before changing provider records.

## Boundary Routes

| Pressure | Route |
| --- | --- |
| connector source policy | `connector/SOURCE_POLICY.md` |
| storage posture | `connector/STORAGE_POLICY.md` |
| permission and public-method boundary | `BOUNDARIES.md` |
| runtime/MCP wrapper contract | `docs/RUNTIME_CONTRACT.md` |
| shared KAG schema, registry, composition, validation | `aoa-kag` |
| runtime serving and local state | `abyss-stack` or connector storage roots |

## Validation

Use the owner validator named in `manifest.json`, then validate this provider
through the `aoa-kag` local subtree validator.

## Closeout

Report provider records changed, source-return route changed, owner validation,
`aoa-kag` validation, and the next MCP consumer route.
