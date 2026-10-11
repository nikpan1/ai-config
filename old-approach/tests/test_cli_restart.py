import json
import subprocess
import sys

from docgen.storage import atomic_write, write_json


def test_review_resumes_in_another_process_without_model_calls(tmp_path):
    source = tmp_path / "source"
    source.mkdir()
    atomic_write(source / "diagram.bin", b"fixture-only asset")
    environment = tmp_path / "runtime.env"
    workspace = tmp_path / "artifacts"
    atomic_write(
        environment,
        f"GEMINI_API_KEY=test-key\nGEMINI_MODEL=gemini-3.8-flash\n"
        f"DOCGEN_WORKSPACE={workspace.as_posix()}\n"
        f"DOCGEN_BUDGET_LEDGER={(workspace / 'budget.sqlite').as_posix()}\n",
    )
    command = [sys.executable, "-m", "docgen.cli", "--env-file", str(environment)]
    run = subprocess.run(
        [*command, "run", str(source), "--thread-id", "process-test"],
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert run.returncode == 2, run.stderr
    status = json.loads(run.stdout)
    issue = status["interrupts"][0]["issues"][0]
    decision_path = tmp_path / "decisions.json"
    write_json(
        decision_path,
        {
            "decisions": [
                {
                    "issue_id": issue["id"],
                    "revision": issue["revision"],
                    "action": "exclude",
                    "reviewer": "automated process fixture",
                    "rationale": "The generated binary fixture has no factual content",
                }
            ]
        },
    )
    resumed = subprocess.run(
        [*command, "resume", "--thread-id", "process-test", "--decisions", str(decision_path)],
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert resumed.returncode == 0, resumed.stderr
    assert json.loads(resumed.stdout)["values"]["status"] == "complete"
    budget = subprocess.run([*command, "budget"], capture_output=True, text=True, timeout=30)
    assert json.loads(budget.stdout)["charged_pln"] == 0
    history = subprocess.run(
        [*command, "history", "--thread-id", "process-test"],
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert len(json.loads(history.stdout)) >= 5
