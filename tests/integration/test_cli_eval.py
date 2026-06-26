import json
import subprocess
import sys


def _run(*args: str) -> dict[str, object]:
    completed = subprocess.run(
        [sys.executable, "-m", "aoa_telegram_connector.cli", *args],
        check=True,
        text=True,
        capture_output=True,
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
    assert query["results"]
    answer = _run("answer", "vendor_boot bootloop warning", "--run", "pytest-fixture")
    assert answer["answer_report"]["answer_status"] == "answered"
    assert _run("eval", "permissions")["status"] == "pass"
    assert _run("eval", "answer-packets")["status"] == "pass"
