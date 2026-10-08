import json
import subprocess
import sys
from pathlib import Path

from planning_fixtures import knowledge_fixture

from docgen.storage import atomic_write, write_json


def test_separate_process_planning_restart_and_workflow_dispatch(tmp_path, settings, store):
    bundle = knowledge_fixture(tmp_path, settings, store)
    environment = tmp_path / "runtime.env"
    atomic_write(
        environment,
        f"GEMINI_MODEL=gemini-3.8-flash\nDOCGEN_WORKSPACE={store.root.as_posix()}\n"
        f"DOCGEN_BUDGET_LEDGER={settings.budget_ledger.as_posix()}\n",
    )
    tests = Path(__file__).parent.resolve()
    bootstrap = (
        "import sys; sys.path.insert(0, sys.argv.pop(1)); "
        "from planning_fixtures import PlanningFixtureModel; import docgen.cli as cli; "
        "cli.GeminiModel = lambda *args: PlanningFixtureModel(); raise SystemExit(cli.main())"
    )
    command = [sys.executable, "-c", bootstrap, str(tests), "--env-file", str(environment)]

    def execute(arguments):
        result = subprocess.run([*command, *arguments], capture_output=True, text=True, timeout=45)
        assert result.returncode == 0, result.stderr
        return json.loads(result.stdout)

    result = execute(
        [
            "plan-documentation",
            "--knowledge",
            bundle,
            "--template",
            str(tests.parent / "data/template.md"),
            "--thread-id",
            "process-plan",
            "--stop-after",
            "snapshot_planning_inputs",
        ]
    )
    assert result["next"] == ["compile_template"]
    for stage in [
        "compile_template",
        "inventory_content",
        "discover_documentation_units",
        "verify_documentation_units",
        "plan_logical_structure",
        "allocate_content",
        "design_page_tree",
        "write_section_briefs",
        "plan_navigation",
        "plan_writing_jobs",
        "validate_plan",
        "audit_plan",
    ]:
        result = execute(["resume", "--thread-id", "process-plan", "--stop-after", stage])
    result = execute(["resume", "--thread-id", "process-plan"])
    assert result["values"]["status"] == "ready_for_generation"
    history = execute(["history", "--thread-id", "process-plan", "--limit", "1000"])
    assert len(history) >= 50
    assert {name for item in history for name in item["next"]} >= {
        "compile_template",
        "discover_documentation_units",
        "verify_documentation_units",
        "write_section_briefs",
        "audit_plan",
        "finalize_plan",
    }
    metadata = store.path("runs/process-plan/workflow.json")
    value = json.loads(metadata.read_text())
    assert value["workflow"] == "documentation_planning"
    collision = subprocess.run(
        [*command, "run", str(tmp_path), "--thread-id", "process-plan"],
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert collision.returncode == 1
    assert "another workflow" in collision.stderr
    write_json(tmp_path / "brief.json", {"purpose": "Different revision"})
    duplicate = subprocess.run(
        [
            *command,
            "plan-documentation",
            "--knowledge",
            bundle,
            "--template",
            str(tests.parent / "data/template.md"),
            "--thread-id",
            "process-plan",
            "--brief",
            str(tmp_path / "brief.json"),
        ],
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert duplicate.returncode == 1
    assert "Thread already exists" in duplicate.stderr
