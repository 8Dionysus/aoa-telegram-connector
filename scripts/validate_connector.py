#!/usr/bin/env python3
"""Validate the GitHub-publishable Telegram connector skeleton."""

from __future__ import annotations

import json
import sys
from pathlib import Path


REQUIRED_FILES = [
    "AGENTS.md",
    "README.md",
    "CHARTER.md",
    "BOUNDARIES.md",
    "ROADMAP.md",
    "CHANGELOG.md",
    "pyproject.toml",
    ".env.example",
    ".gitignore",
    ".connector-state/AGENTS.md",
    ".connector-state/README.md",
    "connector/SOURCE_POLICY.md",
    "connector/STORAGE_POLICY.md",
    "connector/manifests/connector_manifest.yaml",
    "connector/manifests/route_allowlist.yaml",
    "connector/manifests/artifact_classes.yaml",
    "connector/profiles/starter-permissioned.yaml",
    "connector/seeds/starter_conversations.yaml",
    "connector/fixtures/telegram/starter_conversation.json",
    "docs/ARCHITECTURE.md",
    "docs/INSTALL.md",
    "docs/AGENT_INSTALL_ROUTE.md",
    "docs/QUERY_MODEL.md",
    "docs/GRAPH_MODEL.md",
    "docs/RUNTIME_CONTRACT.md",
    "docs/MCP_ROLLOUT.md",
    "docs/STARTER_PROOF.md",
    "docs/CONNECTOR_FAMILY_CLAIM_CONTRACT.md",
    "docs/decisions/README.md",
    "docs/decisions/AOA-TELEGRAM-D-0001-permissioned-conversation-proof.md",
    "evals/AGENTS.md",
    "evals/PORT.yaml",
    "evals/suites/README.md",
    "evals/suites/connector-family-claim-runtime.suite.md",
    "evals/suites/starter_claim_conflict_relations.json",
    "evals/suites/starter_claim_answer_packets.json",
    "kag/AGENTS.md",
    "kag/README.md",
    "kag/manifest.json",
    "kag/nodes/source_home.json",
    "kag/nodes/storage_boundary.json",
    "kag/edges/source_routes_to_storage_boundary.json",
    "kag/indexes/source_inventory.json",
    "kag/indexes/source_surface_index.json",
    "kag/projections/source_return.json",
    "kag/receipts/validation_receipt.json",
    "src/aoa_telegram_connector/cli.py",
]

REQUIRED_DIRS = [
    ".connector-state",
    ".connector-state/data",
    ".connector-state/cache",
    ".connector-state/artifacts",
    "src/aoa_telegram_connector/parse",
    "src/aoa_telegram_connector/normalize",
    "src/aoa_telegram_connector/index",
    "src/aoa_telegram_connector/graph",
    "src/aoa_telegram_connector/claims",
    "src/aoa_telegram_connector/answer",
    "src/aoa_telegram_connector/query",
    "src/aoa_telegram_connector/evaluation",
    "src/aoa_telegram_connector/storage",
    "src/aoa_telegram_connector/sources",
    "tests/unit",
    "tests/contract",
    "tests/integration",
    "evals/intake",
    "evals/reports",
    "kag",
    "kag/nodes",
    "kag/edges",
    "kag/indexes",
    "kag/projections",
    "kag/receipts",
]

REQUIRED_SCHEMAS = [
    "crawl_receipt.schema.json",
    "normalized_topic.schema.json",
    "normalized_post.schema.json",
    "normalized_conversation.schema.json",
    "normalized_message.schema.json",
    "permission_state.schema.json",
    "evidence_packet.schema.json",
    "answer_packet.schema.json",
    "materialize_receipt.schema.json",
    "index_manifest.schema.json",
    "graph_node.schema.json",
    "graph_edge.schema.json",
    "claim.schema.json",
    "claim_relation.schema.json",
    "conflict_report.schema.json",
    "freshness_report.schema.json",
    "applicability_report.schema.json",
    "warning_report.schema.json",
    "source_registry.schema.json",
    "source_sync_plan.schema.json",
]

REQUIRED_GITIGNORE = [
    ".connector-state/*",
    "!.connector-state/README.md",
    "!.connector-state/AGENTS.md",
    "!.connector-state/data/",
    "!.connector-state/cache/",
    "!.connector-state/artifacts/",
    ".connector-state/data/*",
    ".connector-state/cache/*",
    ".connector-state/artifacts/*",
    "!.connector-state/data/.gitkeep",
    "!.connector-state/cache/.gitkeep",
    "!.connector-state/artifacts/.gitkeep",
    "data/",
    "cache/",
    "artifacts/",
    "raw/",
    "indexes/",
    "vectors/",
    "graphs/",
    "exports/full/",
    "!kag/indexes/",
    "!kag/indexes/*.json",
    "*.sqlite",
    "*.sqlite3",
    "*.parquet",
    "*.qdrant/",
    "*.lancedb/",
]

FORBIDDEN_HEAVY_ROOTS = {"data", "cache", "artifacts", "raw", "indexes", "vectors", "graphs", "exports"}
IGNORED_LOCAL_CACHE_DIR_NAMES = {"__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache", ".venv"}


def main() -> int:
    repo_root = Path(__file__).resolve().parents[1]
    errors: list[str] = []
    warnings: list[str] = []

    for rel in REQUIRED_FILES:
        if not (repo_root / rel).is_file():
            errors.append(f"missing required file: {rel}")
    for rel in REQUIRED_DIRS:
        if not (repo_root / rel).is_dir():
            errors.append(f"missing required directory: {rel}")

    schema_dir = repo_root / "connector" / "schemas"
    for name in REQUIRED_SCHEMAS:
        path = schema_dir / name
        if not path.is_file():
            errors.append(f"missing schema: connector/schemas/{name}")
        else:
            _load_json(path, errors)

    for path in [*repo_root.glob("connector/fixtures/**/*.json"), *repo_root.glob("evals/suites/**/*.json")]:
        _load_json(path, errors)

    gitignore = (repo_root / ".gitignore").read_text(encoding="utf-8") if (repo_root / ".gitignore").exists() else ""
    for pattern in REQUIRED_GITIGNORE:
        if pattern not in gitignore:
            errors.append(f".gitignore missing heavy-data pattern: {pattern}")

    for rel in FORBIDDEN_HEAVY_ROOTS:
        if (repo_root / rel).exists():
            errors.append(f"heavy artifact path exists inside repository: {rel}")
    for path in repo_root.rglob("*"):
        if ".git" in path.parts:
            continue
        rel_parts = path.relative_to(repo_root).parts
        if any(part in IGNORED_LOCAL_CACHE_DIR_NAMES for part in rel_parts):
            continue
        if rel_parts and rel_parts[0] == ".connector-state":
            continue
        if path.is_dir() and path.name in FORBIDDEN_HEAVY_ROOTS and not _is_allowed_kag_provider_dir(rel_parts):
            errors.append(f"forbidden artifact directory exists inside repository: {path.relative_to(repo_root)}")

    _check_text(repo_root, errors, warnings)
    _check_eval_port(repo_root, errors)

    payload = {
        "schema": "aoa_telegram_connector_validation_v1",
        "status": "ok" if not errors else "error",
        "repo_root": str(repo_root),
        "errors": errors,
        "warnings": warnings,
        "checked": {
            "required_files": len(REQUIRED_FILES),
            "required_dirs": len(REQUIRED_DIRS),
            "schemas": len(REQUIRED_SCHEMAS),
        },
    }
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0 if not errors else 1


def _is_allowed_kag_provider_dir(rel_parts: tuple[str, ...]) -> bool:
    return len(rel_parts) == 2 and rel_parts[0] == "kag" and rel_parts[1] == "indexes"


def _load_json(path: Path, errors: list[str]) -> None:
    try:
        json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        errors.append(f"invalid json {path}: {exc}")


def _check_text(repo_root: Path, errors: list[str], warnings: list[str]) -> None:
    source_policy = (repo_root / "connector" / "SOURCE_POLICY.md").read_text(encoding="utf-8")
    route_policy = (repo_root / "connector" / "manifests" / "route_allowlist.yaml").read_text(encoding="utf-8")
    storage_policy = (repo_root / "connector" / "STORAGE_POLICY.md").read_text(encoding="utf-8")
    runtime_contract = (repo_root / "docs" / "RUNTIME_CONTRACT.md").read_text(encoding="utf-8")
    doctrine = (repo_root / "docs" / "CONNECTOR_FAMILY_CLAIM_CONTRACT.md").read_text(encoding="utf-8")

    for token in ["bot api", "tdlib", "mtproto", "takeout", "account", "private messages", "paid_member", "saved messages", "attachments", "download", "write", "internal search"]:
        if token not in source_policy.casefold():
            errors.append(f"source policy missing denied token: {token}")

    for token in ["bot_api", "tdlib_user_session", "mtproto_user_session", "takeout_export", "private_dm", "paid", "saved_messages", "download", "write", "internal-search"]:
        if token not in route_policy:
            errors.append(f"route allowlist missing denied token: {token}")

    for var in ["CONNECTOR_FAMILY_ROOT", "CONNECTOR_INSTANCE_ROOT", "CONNECTOR_DATA_ROOT", "CONNECTOR_CACHE_ROOT", "CONNECTOR_ARTIFACT_ROOT"]:
        if var not in storage_policy or var not in (repo_root / ".env.example").read_text(encoding="utf-8"):
            errors.append(f"storage root variable missing from docs/env: {var}")

    for token in [
        "aoa-telegram-connector-mcp",
        "agent_answer",
        "evidence_chain",
        "permission_report",
        "conflict_report",
        "freshness_report",
        "applicability_report",
        "warning_report",
        "network_touched=false",
        "read_only=true",
        "internal-search source route",
    ]:
        if token not in runtime_contract:
            errors.append(f"runtime contract missing token: {token}")

    for token in ["conversation", "message", "permission_state", "insufficient_permission", "insufficient_evidence", "warning_report", "freshness_report"]:
        if token not in doctrine:
            errors.append(f"connector-family doctrine missing token: {token}")

    if "robots" in source_policy.casefold():
        warnings.append("robots policy is advisory only; keep hard source boundaries explicit")


def _check_eval_port(repo_root: Path, errors: list[str]) -> None:
    port = (repo_root / "evals" / "PORT.yaml").read_text(encoding="utf-8")
    for token in [
        "schema_version: local_eval_port_v1",
        "owner_repo: aoa-telegram-connector",
        "proof_owner_repo: aoa-evals",
        "no verdict, scoring, regression, or proof doctrine authority",
    ]:
        if token not in port:
            errors.append(f"eval port missing boundary token: {token}")

    expected_suites = {
        "starter_claim_conflict_relations.json": "aoa_telegram_permission_eval_suite_v1",
        "starter_claim_answer_packets.json": "aoa_telegram_answer_eval_suite_v1",
    }
    for suite_name, schema in expected_suites.items():
        suite = json.loads((repo_root / "evals" / "suites" / suite_name).read_text(encoding="utf-8"))
        if suite.get("schema") != schema:
            errors.append(f"{suite_name} has unexpected schema")
        if suite.get("proof_owner_repo") != "aoa-evals":
            errors.append(f"{suite_name} must keep aoa-evals as proof owner")
        if not suite.get("cases"):
            errors.append(f"{suite_name} must include at least one case")


if __name__ == "__main__":
    sys.exit(main())
