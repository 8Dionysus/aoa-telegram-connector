# Changelog

## Unreleased

- Added operator-local Telegram source registry commands for public, paid,
  private, and Saved Messages sources.
- Added source sync planning and multi-source MTProto sync receipts with media
  downloads disabled by default.
- Preserved MTProto `source_receipt` and media policy through normalize, index,
  query, and answer evidence paths.

## 0.1.0

- Initial permissioned Telegram conversation connector skeleton.
- Added synthetic fixture, local normalize/index/graph/query/answer proof, and
  permission-aware evals.
