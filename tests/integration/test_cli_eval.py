import json
import os
import subprocess
import sys


def _run(*args: str, env: dict[str, str] | None = None) -> dict[str, object]:
    completed = subprocess.run(
        [sys.executable, "-m", "aoa_telegram_connector.cli", *args],
        check=True,
        text=True,
        capture_output=True,
        env=env,
    )
    return json.loads(completed.stdout)


def test_cli_materialize_build_query_answer_and_eval() -> None:
    materialize = _run("materialize", "fixture", "--run", "pytest-fixture", "--mode", "tdlib_user_session")
    assert materialize["network_touched"] is False
    index = _run("build-index", "--run", "pytest-fixture")
    assert index["doc_count"] >= 3
    graph = _run("build-graph", "--run", "pytest-fixture")
    assert graph["edge_count"] >= 6
    query = _run("query-graph", "vendor_boot bootloop warning", "--run", "pytest-fixture")
    assert query["network_touched"] is False
    assert query["read_only"] is True
    assert query["results"]
    answer = _run("answer", "vendor_boot bootloop warning", "--run", "pytest-fixture")
    assert answer["network_touched"] is False
    assert answer["read_only"] is True
    assert answer["answer_report"]["answer_status"] == "answered"
    assert _run("eval", "permissions")["status"] == "pass"
    assert _run("eval", "answer-packets")["status"] == "pass"


def test_cli_materializes_telegram_desktop_export_and_answers() -> None:
    source = "connector/fixtures/telegram/telegram_desktop_export_result.json"
    run = "pytest-desktop-export"
    materialize = _run("materialize", "telegram-desktop-export", source, "--run", run)
    assert materialize["schema"] == "aoa_telegram_desktop_export_materialize_receipt_v1"
    assert materialize["mode"] == "takeout_export"
    assert materialize["network_touched"] is False
    assert materialize["read_only"] is True
    assert materialize["message_count"] == 2
    index = _run("build-index", "--run", run)
    assert index["doc_count"] == 2
    graph = _run("build-graph", "--run", run)
    assert graph["edge_count"] >= 5
    query = _run("query-graph", "vendor_boot bootloop warning", "--run", run)
    assert query["read_only"] is True
    assert query["results"]
    answer = _run("answer", "vendor_boot bootloop warning", "--run", run)
    assert answer["answer_report"]["answer_status"] == "answered"
    assert answer["warning_report"]["status"] == "warning_supported"


def test_cli_mtproto_history_requires_local_credentials() -> None:
    env = os.environ.copy()
    env.pop("TELEGRAM_API_ID", None)
    env.pop("TELEGRAM_API_HASH", None)
    completed = subprocess.run(
        [sys.executable, "-m", "aoa_telegram_connector.cli", "materialize", "mtproto-history", "@aoa_android_lab", "--run", "pytest-mtproto"],
        check=False,
        text=True,
        capture_output=True,
        env=env,
    )
    assert completed.returncode == 2
    payload = json.loads(completed.stdout)
    assert payload["status"] == "error"
    assert payload["error"] == "missing_mtproto_credentials"
    assert payload["network_touched"] is False


def test_cli_sources_registry_plans_owned_source_sync(tmp_path) -> None:
    env = os.environ.copy()
    env["CONNECTOR_DATA_ROOT"] = str(tmp_path / "data")
    env["CONNECTOR_CACHE_ROOT"] = str(tmp_path / "cache")
    env["CONNECTOR_ARTIFACT_ROOT"] = str(tmp_path / "artifacts")
    env.pop("TELEGRAM_API_ID", None)
    env.pop("TELEGRAM_API_HASH", None)

    channel = _run(
        "sources",
        "add",
        "@aoa_ai_radar",
        "--kind",
        "channel",
        "--access",
        "public",
        "--tags",
        "ai,agents",
        "--trust-score",
        "0.8",
        env=env,
    )
    assert channel["status"] == "ok"
    assert channel["source"]["access"] == "public"
    saved = _run("sources", "add", "me", "--kind", "saved_messages", "--tags", "self,notes", "--trust-score", "1.0", env=env)
    assert saved["source"]["access"] == "self_saved"

    listed = _run("sources", "list", env=env)
    assert listed["selected_count"] == 2
    plan = _run("sources", "plan", "--run", "pytest-owned-sources", "--limit", "25", env=env)
    assert plan["schema"] == "aoa_telegram_source_sync_plan_v1"
    assert plan["selected_count"] == 2
    assert all(step["include_media"] == "none" for step in plan["steps"])

    completed = subprocess.run(
        [sys.executable, "-m", "aoa_telegram_connector.cli", "sources", "sync", "--run", "pytest-owned-sources", "--limit", "25"],
        check=False,
        text=True,
        capture_output=True,
        env=env,
    )
    assert completed.returncode == 2
    payload = json.loads(completed.stdout)
    assert payload["error"] == "missing_mtproto_credentials"
    assert payload["selected_count"] == 2
    assert payload["network_touched"] is False
