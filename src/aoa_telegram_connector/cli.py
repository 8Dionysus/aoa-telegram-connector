"""Command line interface for the Telegram conversation connector."""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import shutil
from datetime import UTC, datetime
from pathlib import Path

from aoa_telegram_connector.answer import render_answer_packet
from aoa_telegram_connector.config import StorageRoots, find_repo_root
from aoa_telegram_connector.graph import build_graph
from aoa_telegram_connector.index import build_keyword_index
from aoa_telegram_connector.normalize import DEFAULT_MODE, SUPPORTED_MODES, normalize_snapshot
from aoa_telegram_connector.parse.mtproto_history import MtprotoCredentials, load_mtproto_history
from aoa_telegram_connector.parse.telegram_desktop_export import find_export_json, load_telegram_desktop_export
from aoa_telegram_connector.policy.rules import route_decision
from aoa_telegram_connector.query import query_graph_packet, query_keyword_index
from aoa_telegram_connector.storage import create_storage_roots, storage_status
from aoa_telegram_connector.sources import (
    ACCESS_MODES,
    MEDIA_POLICIES,
    SOURCE_KINDS,
    build_sync_plan,
    effective_media_policy,
    load_registry,
    parse_csv,
    registry_path,
    select_sources,
    source_private_flag,
    upsert_source,
)


DEFAULT_PROFILE = "starter-permissioned"
DEFAULT_RUN = "starter-fixture"
FIXTURE = Path("connector/fixtures/telegram/starter_conversation.json")


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return int(args.func(args))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="aoa-telegram")
    sub = parser.add_subparsers(dest="command", required=True)

    doctor = sub.add_parser("doctor")
    doctor.set_defaults(func=cmd_doctor)

    init = sub.add_parser("init")
    init.set_defaults(func=cmd_init)

    storage = sub.add_parser("storage")
    storage_sub = storage.add_subparsers(dest="storage_command", required=True)
    storage_status_parser = storage_sub.add_parser("status")
    storage_status_parser.add_argument("--measure", action="store_true")
    storage_status_parser.set_defaults(func=cmd_storage_status)

    sources = sub.add_parser("sources")
    sources_sub = sources.add_subparsers(dest="sources_command", required=True)
    sources_add = sources_sub.add_parser("add")
    sources_add.add_argument("source_ref", help="Telegram @username, t.me link, numeric id, or me for Saved Messages")
    sources_add.add_argument("--kind", choices=sorted(SOURCE_KINDS), required=True)
    sources_add.add_argument("--access", choices=sorted(ACCESS_MODES))
    sources_add.add_argument("--title")
    sources_add.add_argument("--tags", default="")
    sources_add.add_argument("--trust-score", type=float)
    sources_add.add_argument("--include-media", choices=sorted(MEDIA_POLICIES), default="none")
    sources_add.add_argument("--scope")
    sources_add.add_argument("--notes")
    sources_add.add_argument("--disabled", action="store_true")
    sources_add.set_defaults(func=cmd_sources_add)
    sources_list = sources_sub.add_parser("list")
    _add_source_filter_args(sources_list)
    sources_list.add_argument("--all", action="store_true", help="include disabled sources")
    sources_list.set_defaults(func=cmd_sources_list)
    sources_plan = sources_sub.add_parser("plan-sync")
    sources_plan.add_argument("--run", default="telegram-owned-sources")
    sources_plan.add_argument("--limit", type=int, default=200)
    sources_plan.add_argument("--include-media", choices=sorted(MEDIA_POLICIES))
    _add_source_filter_args(sources_plan)
    sources_plan.add_argument("--all", action="store_true", help="include disabled sources")
    sources_plan.set_defaults(func=cmd_sources_plan_sync)
    sources_plan_alias = sources_sub.add_parser("plan")
    sources_plan_alias.add_argument("--run", default="telegram-owned-sources")
    sources_plan_alias.add_argument("--limit", type=int, default=200)
    sources_plan_alias.add_argument("--include-media", choices=sorted(MEDIA_POLICIES))
    _add_source_filter_args(sources_plan_alias)
    sources_plan_alias.add_argument("--all", action="store_true", help="include disabled sources")
    sources_plan_alias.set_defaults(func=cmd_sources_plan_sync)
    sources_sync = sources_sub.add_parser("sync")
    sources_sync.add_argument("--run", default="telegram-owned-sources")
    sources_sync.add_argument("--profile", default=DEFAULT_PROFILE)
    sources_sync.add_argument("--limit", type=int, default=200)
    sources_sync.add_argument("--include-media", choices=sorted(MEDIA_POLICIES))
    sources_sync.add_argument("--session-path")
    sources_sync.add_argument("--api-id-env", default="TELEGRAM_API_ID")
    sources_sync.add_argument("--api-hash-env", default="TELEGRAM_API_HASH")
    sources_sync.add_argument("--phone-env", default="TELEGRAM_PHONE")
    _add_source_filter_args(sources_sync)
    sources_sync.add_argument("--all", action="store_true", help="include disabled sources")
    sources_sync.set_defaults(func=cmd_sources_sync)

    policy = sub.add_parser("policy")
    policy_sub = policy.add_subparsers(dest="policy_command", required=True)
    policy_check = policy_sub.add_parser("check")
    policy_check.set_defaults(func=cmd_policy_check)

    materialize = sub.add_parser("materialize")
    materialize_sub = materialize.add_subparsers(dest="materialize_command", required=True)
    fixture = materialize_sub.add_parser("fixture")
    fixture.add_argument("--run", default=DEFAULT_RUN)
    fixture.add_argument("--profile", default=DEFAULT_PROFILE)
    fixture.add_argument("--mode", choices=sorted(SUPPORTED_MODES), default=DEFAULT_MODE)
    fixture.set_defaults(func=cmd_materialize_fixture)
    desktop_export = materialize_sub.add_parser("telegram-desktop-export")
    desktop_export.add_argument("source", help="Telegram Desktop export result.json or export directory")
    desktop_export.add_argument("--run", default="telegram-desktop-export-pilot")
    desktop_export.add_argument("--profile", default=DEFAULT_PROFILE)
    desktop_export.add_argument("--conversation-id")
    desktop_export.add_argument("--title")
    desktop_export.add_argument("--scope", default="operator_selected_telegram_desktop_export")
    desktop_export.add_argument("--private", action="store_true", help="mark this operator-selected export as private account evidence")
    desktop_export.add_argument("--limit", type=int)
    desktop_export.set_defaults(func=cmd_materialize_telegram_desktop_export)
    mtproto_history = materialize_sub.add_parser("mtproto-history")
    mtproto_history.add_argument("chat", help="Telegram username, invite-visible peer, numeric id, or t.me link")
    mtproto_history.add_argument("--run", default="mtproto-history-pilot")
    mtproto_history.add_argument("--profile", default=DEFAULT_PROFILE)
    mtproto_history.add_argument("--limit", type=int, default=200)
    mtproto_history.add_argument("--conversation-id")
    mtproto_history.add_argument("--title")
    mtproto_history.add_argument("--scope", default="operator_selected_mtproto_history")
    mtproto_history.add_argument("--private", action="store_true", help="mark this operator-selected scope as private account evidence")
    mtproto_history.add_argument("--session-path")
    mtproto_history.add_argument("--api-id-env", default="TELEGRAM_API_ID")
    mtproto_history.add_argument("--api-hash-env", default="TELEGRAM_API_HASH")
    mtproto_history.add_argument("--phone-env", default="TELEGRAM_PHONE")
    mtproto_history.set_defaults(func=cmd_materialize_mtproto_history)

    build_index = sub.add_parser("build-index")
    build_index.add_argument("--run", default=DEFAULT_RUN)
    build_index.add_argument("--profile", default=DEFAULT_PROFILE)
    build_index.set_defaults(func=cmd_build_index)

    build_graph_parser = sub.add_parser("build-graph")
    build_graph_parser.add_argument("--run", default=DEFAULT_RUN)
    build_graph_parser.add_argument("--profile", default=DEFAULT_PROFILE)
    build_graph_parser.set_defaults(func=cmd_build_graph)

    query = sub.add_parser("query")
    query.add_argument("query")
    query.add_argument("--run", default=DEFAULT_RUN)
    query.add_argument("--limit", type=int, default=5)
    query.set_defaults(func=cmd_query)

    query_graph = sub.add_parser("query-graph")
    query_graph.add_argument("query")
    query_graph.add_argument("--run", default=DEFAULT_RUN)
    query_graph.add_argument("--limit", type=int, default=5)
    query_graph.set_defaults(func=cmd_query_graph)

    answer = sub.add_parser("answer")
    answer.add_argument("query")
    answer.add_argument("--run", default=DEFAULT_RUN)
    answer.add_argument("--limit", type=int, default=5)
    answer.set_defaults(func=cmd_answer)

    eval_parser = sub.add_parser("eval")
    eval_sub = eval_parser.add_subparsers(dest="eval_command", required=True)
    eval_sub.add_parser("permissions").set_defaults(func=cmd_eval_permissions)
    eval_sub.add_parser("answer-packets").set_defaults(func=cmd_eval_answer_packets)
    return parser


def _add_source_filter_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--source", action="append", dest="source_refs", help="filter by source_ref; repeatable")
    parser.add_argument("--kind", action="append", choices=sorted(SOURCE_KINDS), dest="kinds", help="filter by source kind; repeatable")
    parser.add_argument("--tag", action="append", dest="tags", help="filter by tag; repeatable")


def cmd_doctor(_args: argparse.Namespace) -> int:
    repo_root = find_repo_root()
    required = ["AGENTS.md", "README.md", "connector/SOURCE_POLICY.md", "connector/STORAGE_POLICY.md", str(FIXTURE), "docs/RUNTIME_CONTRACT.md"]
    missing = [rel for rel in required if not (repo_root / rel).exists()]
    _emit(
        {
            "schema": "aoa_telegram_doctor_v1",
            "status": "ok" if not missing else "error",
            "repo_root": str(repo_root),
            "missing": missing,
            "storage": storage_status(repo_root, StorageRoots.from_env(repo_root)),
            "network_touched": False,
            "read_only": True,
        }
    )
    return 0 if not missing else 1


def cmd_init(_args: argparse.Namespace) -> int:
    roots = StorageRoots.from_env(find_repo_root())
    _emit({"schema": "aoa_telegram_init_v1", "status": "ok", "created": create_storage_roots(roots), "network_touched": False})
    return 0


def cmd_storage_status(args: argparse.Namespace) -> int:
    repo_root = find_repo_root()
    _emit(storage_status(repo_root, StorageRoots.from_env(repo_root), measure=args.measure))
    return 0


def cmd_sources_add(args: argparse.Namespace) -> int:
    roots = StorageRoots.from_env(find_repo_root())
    create_storage_roots(roots)
    try:
        source, path, state = upsert_source(
            roots.data,
            source_ref=args.source_ref,
            kind=args.kind,
            access=args.access,
            title=args.title,
            tags=parse_csv(args.tags),
            trust_score=args.trust_score,
            include_media=args.include_media,
            enabled=not args.disabled,
            scope=args.scope,
            notes=args.notes,
        )
    except ValueError as exc:
        _emit({"schema": "aoa_telegram_source_registry_receipt_v1", "status": "error", "error": str(exc), "network_touched": False, "read_only": True})
        return 2
    _emit(
        {
            "schema": "aoa_telegram_source_registry_receipt_v1",
            "status": "ok",
            "state": state,
            "registry_path": str(path),
            "source": source,
            "network_touched": False,
            "read_only": True,
        }
    )
    return 0


def cmd_sources_list(args: argparse.Namespace) -> int:
    roots = StorageRoots.from_env(find_repo_root())
    registry = load_registry(roots.data)
    selected = _selected_sources(registry, args)
    _emit(
        {
            "schema": "aoa_telegram_source_registry_list_v1",
            "status": "ok",
            "registry_path": str(registry_path(roots.data)),
            "source_count": len(registry.get("sources", [])),
            "selected_count": len(selected),
            "sources": selected,
            "network_touched": False,
            "read_only": True,
        }
    )
    return 0


def cmd_sources_plan_sync(args: argparse.Namespace) -> int:
    roots = StorageRoots.from_env(find_repo_root())
    registry = load_registry(roots.data)
    selected = _selected_sources(registry, args)
    plan = build_sync_plan(run_id=args.run, sources=selected, limit=args.limit, include_media=args.include_media)
    path = roots.artifact / "sync-plans" / args.run / "telegram-source-sync-plan.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(plan, indent=2, sort_keys=True), encoding="utf-8")
    _emit({"status": "ok" if selected else "no_sources", "plan_path": str(path), **plan})
    return 0 if selected else 1


def cmd_sources_sync(args: argparse.Namespace) -> int:
    repo_root = find_repo_root()
    roots = StorageRoots.from_env(repo_root)
    create_storage_roots(roots)
    registry = load_registry(roots.data)
    selected = _selected_sources(registry, args)
    if not selected:
        _emit({"schema": "aoa_telegram_source_sync_receipt_v1", "status": "error", "error": "no_sources", "network_touched": False, "read_only": True})
        return 1
    unsupported_media = [source for source in selected if effective_media_policy(source, args.include_media) != "none"]
    if unsupported_media:
        _emit(
            {
                "schema": "aoa_telegram_source_sync_receipt_v1",
                "status": "error",
                "error": "media_download_disabled",
                "source_ids": [source.get("source_id") for source in unsupported_media],
                "network_touched": False,
                "read_only": True,
                "download_touched": False,
            }
        )
        return 2
    credentials = _mtproto_credentials(args)
    if isinstance(credentials, dict):
        _emit({"selected_count": len(selected), "source_ids": [source.get("source_id") for source in selected], **credentials})
        return 2
    session_path = Path(args.session_path).expanduser() if args.session_path else roots.cache / "mtproto" / args.run / "telegram"
    conversations: list[dict[str, object]] = []
    try:
        for source in selected:
            snapshot = asyncio.run(
                load_mtproto_history(
                    chat=str(source["source_ref"]),
                    credentials=credentials,
                    session_path=session_path,
                    limit=args.limit,
                    conversation_id=str(source["conversation_id"]),
                    title=str(source.get("title") or source["source_ref"]),
                    scope=str(source.get("scope") or "operator_selected_telegram_source"),
                    private=source_private_flag(source),
                    conversation_type=str(source.get("conversation_type") or "mtproto_chat"),
                    source_metadata={
                        "source_id": source.get("source_id"),
                        "kind": source.get("kind"),
                        "access": source.get("access"),
                        "tags": source.get("tags", []),
                        "trust_score": source.get("trust_score"),
                        "route": source.get("route"),
                    },
                    include_media="none",
                )
            )
            conversations.extend([conversation for conversation in snapshot.get("conversations", []) if isinstance(conversation, dict)])
    except Exception as exc:
        _emit(
            {
                "schema": "aoa_telegram_source_sync_receipt_v1",
                "status": "error",
                "run_id": args.run,
                "profile_id": args.profile,
                "error": str(exc),
                "selected_count": len(selected),
                "network_touched": True,
                "read_only": True,
                "download_touched": False,
                "write_touched": False,
            }
        )
        return 1

    snapshot = {
        "schema": "aoa_telegram_source_registry_mtproto_snapshot_v1",
        "source_format": "telegram_source_registry_mtproto_sync",
        "run_id": args.run,
        "limit_per_source": args.limit,
        "source_ids": [source.get("source_id") for source in selected],
        "media_policy": {"include_media": "none", "download_default": "disabled"},
        "conversations": conversations,
    }
    run_root = roots.data / "runs" / args.run
    raw_dir = run_root / "raw"
    normalized_dir = run_root / "normalized"
    raw_dir.mkdir(parents=True, exist_ok=True)
    raw_path = raw_dir / "telegram-source-registry-mtproto-snapshot.json"
    raw_path.write_text(json.dumps(snapshot, indent=2, sort_keys=True), encoding="utf-8")
    normalized_path = normalize_snapshot(raw_path, "telegram:source-registry-mtproto", normalized_dir, mode="mtproto_user_session")
    message_count = sum(len(conversation.get("messages", [])) for conversation in conversations)
    receipt = {
        "schema": "aoa_telegram_source_sync_receipt_v1",
        "status": "ok",
        "run_id": args.run,
        "profile_id": args.profile,
        "mode": "mtproto_user_session",
        "source_format": "telegram_source_registry_mtproto_sync",
        "source_count": len(selected),
        "message_count": message_count,
        "raw_path": str(raw_path),
        "normalized_path": str(normalized_path),
        "session_path": str(session_path.expanduser().resolve()),
        "source_ids": [source.get("source_id") for source in selected],
        "created_at": _now(),
        "network_touched": True,
        "read_only": True,
        "download_touched": False,
        "write_touched": False,
    }
    receipt_path = _write_receipt(roots.artifact / "receipts", args.run, "sources-sync", receipt)
    _emit({"receipt": str(receipt_path), **receipt})
    return 0


def cmd_policy_check(_args: argparse.Namespace) -> int:
    samples = [
        "telegram:bot_api:channel:@aoa_android_lab",
        "telegram:tdlib_user_session:dm:self",
        "telegram:mtproto_user_session:channel:@aoa_android_lab",
        "telegram:takeout_export:account:self",
        "telegram:bot_api:private_dm:user123",
        "telegram:write:send_message",
        "telegram:download:attachment",
    ]
    decisions = [route_decision(sample) for sample in samples]
    ok = all(item["allowed"] for item in decisions[:4]) and all(not item["allowed"] for item in decisions[4:])
    _emit({"schema": "aoa_telegram_policy_check_v1", "status": "ok" if ok else "error", "decisions": decisions, "network_touched": False})
    return 0 if ok else 1


def cmd_materialize_fixture(args: argparse.Namespace) -> int:
    repo_root = find_repo_root()
    roots = StorageRoots.from_env(repo_root)
    create_storage_roots(roots)
    source_fixture = repo_root / FIXTURE
    run_root = roots.data / "runs" / args.run
    raw_dir = run_root / "raw"
    normalized_dir = run_root / "normalized"
    raw_dir.mkdir(parents=True, exist_ok=True)
    raw_path = raw_dir / source_fixture.name
    shutil.copyfile(source_fixture, raw_path)
    normalized_path = normalize_snapshot(raw_path, "telegram:fixture", normalized_dir, mode=args.mode)
    receipt = {
        "schema": "aoa_telegram_materialize_receipt_v1",
        "run_id": args.run,
        "profile_id": args.profile,
        "mode": args.mode,
        "fixture": str(FIXTURE),
        "raw_path": str(raw_path),
        "normalized_path": str(normalized_path),
        "created_at": _now(),
        "network_touched": False,
        "read_only": True,
    }
    receipt_path = _write_receipt(roots.artifact / "receipts", args.run, "materialize", receipt)
    _emit({"status": "ok", "receipt": str(receipt_path), **receipt})
    return 0


def cmd_materialize_telegram_desktop_export(args: argparse.Namespace) -> int:
    repo_root = find_repo_root()
    roots = StorageRoots.from_env(repo_root)
    create_storage_roots(roots)
    export_path = find_export_json(Path(args.source))
    snapshot = load_telegram_desktop_export(
        export_path,
        conversation_id=args.conversation_id,
        title=args.title,
        scope=args.scope,
        private=args.private,
        limit=args.limit,
    )
    run_root = roots.data / "runs" / args.run
    raw_dir = run_root / "raw"
    normalized_dir = run_root / "normalized"
    raw_dir.mkdir(parents=True, exist_ok=True)
    raw_path = raw_dir / "telegram-desktop-export-snapshot.json"
    raw_path.write_text(json.dumps(snapshot, indent=2, sort_keys=True), encoding="utf-8")
    normalized_path = normalize_snapshot(raw_path, "telegram:desktop-export", normalized_dir, mode="takeout_export")
    conversation = snapshot["conversations"][0]
    messages = conversation.get("messages", []) if isinstance(conversation, dict) else []
    receipt = {
        "schema": "aoa_telegram_desktop_export_materialize_receipt_v1",
        "run_id": args.run,
        "profile_id": args.profile,
        "mode": "takeout_export",
        "source_format": "telegram_desktop_json_export",
        "source_path": str(export_path),
        "raw_path": str(raw_path),
        "normalized_path": str(normalized_path),
        "conversation_count": len(snapshot.get("conversations", [])),
        "message_count": len(messages),
        "scope": args.scope,
        "private": bool(args.private),
        "created_at": _now(),
        "network_touched": False,
        "read_only": True,
    }
    receipt_path = _write_receipt(roots.artifact / "receipts", args.run, "materialize", receipt)
    _emit({"status": "ok", "receipt": str(receipt_path), **receipt})
    return 0


def cmd_materialize_mtproto_history(args: argparse.Namespace) -> int:
    repo_root = find_repo_root()
    roots = StorageRoots.from_env(repo_root)
    create_storage_roots(roots)
    credentials = _mtproto_credentials(args)
    if isinstance(credentials, dict):
        _emit(credentials)
        return 2
    session_path = Path(args.session_path).expanduser() if args.session_path else roots.cache / "mtproto" / args.run / "telegram"
    try:
        snapshot = asyncio.run(
            load_mtproto_history(
                chat=args.chat,
                credentials=credentials,
                session_path=session_path,
                limit=args.limit,
                conversation_id=args.conversation_id,
                title=args.title,
                scope=args.scope,
                private=args.private,
                conversation_type="private_dm" if args.private else "mtproto_chat",
                include_media="none",
            )
        )
    except Exception as exc:
        _emit(
            {
                "schema": "aoa_telegram_mtproto_materialize_receipt_v1",
                "status": "error",
                "run_id": args.run,
                "profile_id": args.profile,
                "mode": "mtproto_user_session",
                "chat": args.chat,
                "error": str(exc),
                "network_touched": True,
                "read_only": True,
            }
        )
        return 1
    run_root = roots.data / "runs" / args.run
    raw_dir = run_root / "raw"
    normalized_dir = run_root / "normalized"
    raw_dir.mkdir(parents=True, exist_ok=True)
    raw_path = raw_dir / "telegram-mtproto-history-snapshot.json"
    raw_path.write_text(json.dumps(snapshot, indent=2, sort_keys=True), encoding="utf-8")
    normalized_path = normalize_snapshot(raw_path, "telegram:mtproto-history", normalized_dir, mode="mtproto_user_session")
    conversation = snapshot["conversations"][0]
    messages = conversation.get("messages", []) if isinstance(conversation, dict) else []
    receipt = {
        "schema": "aoa_telegram_mtproto_materialize_receipt_v1",
        "status": "ok",
        "run_id": args.run,
        "profile_id": args.profile,
        "mode": "mtproto_user_session",
        "source_format": "telegram_mtproto_history",
        "chat": args.chat,
        "limit": args.limit,
        "raw_path": str(raw_path),
        "normalized_path": str(normalized_path),
        "session_path": str(session_path.expanduser().resolve()),
        "conversation_count": len(snapshot.get("conversations", [])),
        "message_count": len(messages),
        "scope": args.scope,
        "private": bool(args.private),
        "created_at": _now(),
        "network_touched": True,
        "read_only": True,
        "download_touched": False,
        "write_touched": False,
    }
    receipt_path = _write_receipt(roots.artifact / "receipts", args.run, "materialize", receipt)
    _emit({"receipt": str(receipt_path), **receipt})
    return 0


def cmd_build_index(args: argparse.Namespace) -> int:
    roots = StorageRoots.from_env(find_repo_root())
    path = build_keyword_index(roots.data / "runs" / args.run / "normalized", roots.artifact / "indexes" / args.run, profile_id=args.profile)
    index = json.loads(path.read_text(encoding="utf-8"))
    _emit({"schema": "aoa_telegram_index_receipt_v1", "status": "ok", "run_id": args.run, "index_path": str(path), "doc_count": index["doc_count"], "term_count": index["term_count"], "network_touched": False})
    return 0


def cmd_build_graph(args: argparse.Namespace) -> int:
    roots = StorageRoots.from_env(find_repo_root())
    path = build_graph(roots.data / "runs" / args.run / "normalized", roots.artifact / "graphs" / args.run, profile_id=args.profile)
    graph = json.loads(path.read_text(encoding="utf-8"))
    _emit({"schema": "aoa_telegram_graph_receipt_v1", "status": "ok", "run_id": args.run, "graph_path": str(path), "node_count": graph["node_count"], "edge_count": graph["edge_count"], "network_touched": False})
    return 0


def cmd_query(args: argparse.Namespace) -> int:
    roots = StorageRoots.from_env(find_repo_root())
    _emit({"status": "ok", **query_keyword_index(roots.artifact / "indexes" / args.run / "keyword_index.json", args.query, limit=args.limit), "network_touched": False})
    return 0


def cmd_query_graph(args: argparse.Namespace) -> int:
    roots = StorageRoots.from_env(find_repo_root())
    _emit({"status": "ok", **query_graph_packet(roots.artifact / "indexes" / args.run / "keyword_index.json", roots.artifact / "graphs" / args.run / "graph.json", args.query, limit=args.limit), "network_touched": False})
    return 0


def cmd_answer(args: argparse.Namespace) -> int:
    roots = StorageRoots.from_env(find_repo_root())
    packet = query_graph_packet(roots.artifact / "indexes" / args.run / "keyword_index.json", roots.artifact / "graphs" / args.run / "graph.json", args.query, limit=args.limit)
    _emit({"status": "ok", **render_answer_packet(packet), "network_touched": False})
    return 0


def cmd_eval_permissions(_args: argparse.Namespace) -> int:
    bot = _proof("bot_api")
    user = _proof("tdlib_user_session")
    ok = bot["doc_count"] < user["doc_count"] and bot["private_dm_visible"] is False and user["private_dm_visible"] is True
    _emit({"schema": "aoa_telegram_permission_eval_v1", "status": "pass" if ok else "fail", "bot_api": bot, "tdlib_user_session": user, "network_touched": False})
    return 0 if ok else 1


def cmd_eval_answer_packets(_args: argparse.Namespace) -> int:
    run = "eval-answer-fixture"
    roots = _materialize_build(run, "tdlib_user_session")
    warning = render_answer_packet(query_graph_packet(roots.artifact / "indexes" / run / "keyword_index.json", roots.artifact / "graphs" / run / "graph.json", "vendor_boot bootloop warning"))
    missing = render_answer_packet(query_graph_packet(roots.artifact / "indexes" / run / "keyword_index.json", roots.artifact / "graphs" / run / "graph.json", "unicorn modem volte"))
    ok = warning["answer_report"]["answer_status"] == "answered" and warning["warning_report"]["status"] == "warning_supported" and missing["answer_report"]["answer_status"] == "insufficient_evidence"
    _emit({"schema": "aoa_telegram_answer_eval_v1", "status": "pass" if ok else "fail", "cases": [warning["answer_report"], missing["answer_report"]], "network_touched": False})
    return 0 if ok else 1


def _proof(mode: str) -> dict[str, object]:
    run = f"eval-{mode}"
    roots = _materialize_build(run, mode, build_graph_too=False)
    path = roots.artifact / "indexes" / run / "keyword_index.json"
    index = json.loads(path.read_text(encoding="utf-8"))
    return {
        "doc_count": index["doc_count"],
        "private_dm_visible": any(doc.get("conversation_type") == "private_dm" for doc in index.get("docs", [])),
    }


def _materialize_build(run: str, mode: str, build_graph_too: bool = True) -> StorageRoots:
    repo_root = find_repo_root()
    roots = StorageRoots.from_env(repo_root)
    create_storage_roots(roots)
    raw_dir = roots.data / "runs" / run / "raw"
    normalized_dir = roots.data / "runs" / run / "normalized"
    raw_dir.mkdir(parents=True, exist_ok=True)
    raw_path = raw_dir / FIXTURE.name
    shutil.copyfile(repo_root / FIXTURE, raw_path)
    normalize_snapshot(raw_path, "telegram:fixture", normalized_dir, mode=mode)
    build_keyword_index(normalized_dir, roots.artifact / "indexes" / run, profile_id=DEFAULT_PROFILE)
    if build_graph_too:
        build_graph(normalized_dir, roots.artifact / "graphs" / run, profile_id=DEFAULT_PROFILE)
    return roots


def _selected_sources(registry: dict[str, object], args: argparse.Namespace) -> list[dict[str, object]]:
    return select_sources(
        registry,
        source_refs=getattr(args, "source_refs", None),
        kinds=getattr(args, "kinds", None),
        tags=getattr(args, "tags", None),
        enabled_only=not bool(getattr(args, "all", False)),
    )


def _write_receipt(root: Path, run: str, name: str, payload: dict[str, object]) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    path = root / f"{run}-{name}.json"
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return path


def _mtproto_credentials(args: argparse.Namespace) -> MtprotoCredentials | dict[str, object]:
    api_id_raw = os.environ.get(args.api_id_env)
    api_hash = os.environ.get(args.api_hash_env)
    missing = [name for name, value in [(args.api_id_env, api_id_raw), (args.api_hash_env, api_hash)] if not value]
    if missing:
        return {
            "schema": "aoa_telegram_mtproto_materialize_receipt_v1",
            "status": "error",
            "error": "missing_mtproto_credentials",
            "missing_env": missing,
            "network_touched": False,
            "read_only": True,
        }
    try:
        api_id = int(str(api_id_raw))
    except ValueError:
        return {
            "schema": "aoa_telegram_mtproto_materialize_receipt_v1",
            "status": "error",
            "error": f"{args.api_id_env} must be an integer",
            "network_touched": False,
            "read_only": True,
        }
    return MtprotoCredentials(api_id=api_id, api_hash=str(api_hash), phone=os.environ.get(args.phone_env))


def _now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _emit(payload: dict[str, object]) -> None:
    print(json.dumps(payload, indent=2, sort_keys=True))


if __name__ == "__main__":
    raise SystemExit(main())
