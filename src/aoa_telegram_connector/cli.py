"""Command line interface for the Telegram conversation connector."""

from __future__ import annotations

import argparse
import json
import shutil
from datetime import UTC, datetime
from pathlib import Path

from aoa_telegram_connector.answer import render_answer_packet
from aoa_telegram_connector.config import StorageRoots, find_repo_root
from aoa_telegram_connector.graph import build_graph
from aoa_telegram_connector.index import build_keyword_index
from aoa_telegram_connector.normalize import DEFAULT_MODE, SUPPORTED_MODES, normalize_snapshot
from aoa_telegram_connector.policy.rules import route_decision
from aoa_telegram_connector.query import query_graph_packet, query_keyword_index
from aoa_telegram_connector.storage import create_storage_roots, storage_status


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


def cmd_policy_check(_args: argparse.Namespace) -> int:
    samples = [
        "telegram:bot_api:channel:@aoa_android_lab",
        "telegram:tdlib_user_session:dm:self",
        "telegram:takeout_export:account:self",
        "telegram:bot_api:private_dm:user123",
        "telegram:write:send_message",
        "telegram:download:attachment",
    ]
    decisions = [route_decision(sample) for sample in samples]
    ok = all(item["allowed"] for item in decisions[:3]) and all(not item["allowed"] for item in decisions[3:])
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


def _write_receipt(root: Path, run: str, name: str, payload: dict[str, object]) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    path = root / f"{run}-{name}.json"
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return path


def _now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _emit(payload: dict[str, object]) -> None:
    print(json.dumps(payload, indent=2, sort_keys=True))


if __name__ == "__main__":
    raise SystemExit(main())
