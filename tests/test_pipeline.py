import pytest
from conftest import FixtureModel
from langgraph.types import Command

from docgen.contracts import Finding
from docgen.model import TruncatedOutput
from docgen.storage import digest, write_json
from docgen.workflow import Pipeline, persistent_graph


def initial(tmp_path, text="# Rules\n\nArchive once daily unless a hold exists.\n"):
    source = tmp_path / "doc.md"
    source.write_text(text, encoding="utf-8")
    return {"run_id": "test", "source": str(source), "signature": "test", "status": "running"}


def config():
    return {"configurable": {"thread_id": "test"}, "recursion_limit": 10000}


def test_completion_restart_and_no_repeated_model_call(tmp_path, settings, store):
    model = FixtureModel()
    with persistent_graph(Pipeline(settings, store, model), "extract_batch") as graph:
        graph.invoke(initial(tmp_path), config())
        assert model.calls == ["extract"]
        assert graph.get_state(config()).next == ("verify_batch",)
    with persistent_graph(Pipeline(settings, store, model)) as graph:
        result = graph.invoke(None, config())
        assert result["status"] == "complete"
        assert model.calls.count("extract") == 1
        bundle = store.get(result["bundle_ref"])
        assert len(bundle["coverage"]) == 2
        assert not bundle["unresolved_issues"]
        assert len(list(graph.get_state_history(config()))) >= 8


def test_interrupt_defer_and_revision_bound_resume(tmp_path, settings, store):
    state = initial(tmp_path, "# Rules\n\nA [missing definition](absent.md).\n")
    model = FixtureModel()
    with persistent_graph(Pipeline(settings, store, model)) as graph:
        graph.invoke(state, config())
        snapshot = graph.get_state(config())
        assert snapshot.interrupts
        assert model.calls == []
        issue = snapshot.interrupts[0].value["issues"][0]
        decision = {
            "issue_id": issue["id"],
            "revision": issue["revision"],
            "action": "defer",
            "reviewer": "automated fixture",
            "rationale": "Exercise deferral",
        }
        graph.invoke(Command(resume={"decisions": [decision]}), config())
        assert graph.get_state(config()).interrupts
    with persistent_graph(Pipeline(settings, store, model)) as graph:
        decision["action"] = "acknowledge_unknown"
        result = graph.invoke(Command(resume={"decisions": [decision]}), config())
        assert result["status"] == "complete"
        assert store.get(result["decisions_ref"])[-1]["reviewer"] == "automated fixture"


def test_two_repairs_then_pause_unsupported_cannot_be_approved(tmp_path, settings, store):
    def transform(stage, payload, result):
        if stage == "extract":
            result.claims[0].evidence[0].excerpt = "invented source excerpt"
        return result

    model = FixtureModel(transform)
    with persistent_graph(Pipeline(settings, store, model)) as graph:
        graph.invoke(initial(tmp_path), config())
        state = graph.get_state(config())
        assert state.interrupts
        assert model.calls.count("extract") == 3
        issue = state.interrupts[0].value["issues"][0]
        decision = {
            "issue_id": issue["id"],
            "revision": issue["revision"],
            "action": "acknowledge_unknown",
            "reviewer": "fixture",
            "rationale": "Approve",
        }
        with pytest.raises(ValueError, match="unsupported"):
            graph.invoke(Command(resume={"decisions": [decision]}), config())
        assert not graph.get_state(config()).values.get("bundle_ref")


def test_truncation_splits_without_losing_blocks(tmp_path, settings, store):
    def transform(stage, payload, result):
        if stage == "extract" and len(payload["owned"]) > 2:
            raise TruncatedOutput("Fixture truncation")
        return result

    model = FixtureModel(transform)
    with persistent_graph(Pipeline(settings, store, model)) as graph:
        result = graph.invoke(initial(tmp_path, "# Title\n\nOne.\n\nTwo.\n\nThree.\n"), config())
        assert result["status"] == "complete"
        bundle = store.get(result["bundle_ref"])
        assert len(bundle["coverage"]) == 4
        assert len({row["block_id"] for row in bundle["coverage"]}) == 4


def test_independent_verifier_repairs_lost_qualification(tmp_path, settings, store):
    checks = []

    def transform(stage, payload, result):
        if stage == "verify":
            checks.append(stage)
            if len(checks) == 1:
                result.findings = [
                    Finding(
                        kind="omission",
                        description="Hold exception was lost",
                        block_ids=[payload["owned"][-1]["id"]],
                        record_ids=[],
                    )
                ]
        return result

    model = FixtureModel(transform)
    with persistent_graph(Pipeline(settings, store, model)) as graph:
        result = graph.invoke(initial(tmp_path), config())
    assert result["status"] == "complete"
    assert model.calls.count("extract") == 2
    assert model.calls.count("verify") == 2


def test_artifact_tampering_rejected(store):
    ref = store.put({"example": 1})
    store.path(ref).write_text('{"example": 2}', encoding="utf-8")
    with pytest.raises(ValueError, match="integrity"):
        store.get(ref)
    assert digest({"a": 1, "b": 2}) == digest({"b": 2, "a": 1})


def test_cli_can_replace_invalid_review_response(tmp_path, settings, store, monkeypatch):
    from docgen import cli

    model = FixtureModel()
    monkeypatch.setattr(cli, "GeminiModel", lambda *args: model)
    source = initial(tmp_path, "# Rules\n\nA [missing definition](absent.md).\n")["source"]

    def execute(arguments):
        return cli.execute(cli.parser().parse_args(arguments), settings)

    result = execute(["run", source, "--thread-id", "invalid-review"])
    issue = result["interrupts"][0]["issues"][0]
    decision = {
        "issue_id": issue["id"],
        "revision": issue["revision"],
        "action": "acknowledge_unknown",
        "reviewer": "automated fixture",
        "rationale": "The missing linked document remains explicitly unknown",
    }
    path = tmp_path / "decisions.json"
    write_json(path, {"decisions": [decision, decision]})
    arguments = ["resume", "--thread-id", "invalid-review", "--decisions", str(path)]
    with pytest.raises(ValueError, match="Only one decision"):
        execute(arguments)
    assert model.calls == []
    write_json(path, {"decisions": [decision]})
    completed = execute(arguments)
    assert completed["values"]["status"] == "complete"
    assert model.calls.count("extract") == 1
    assert len(store.get(completed["values"]["decisions_ref"])) == 1
    history = execute(["history", "--thread-id", "invalid-review", "--limit", "1000"])
    assert len([item for item in history if "review_issues" in item["next"]]) >= 2


def test_review_gate_deduplicates_identical_findings(settings, store):
    pipeline = Pipeline(settings, store, FixtureModel())
    item = {"kind": "source_issue", "description": "Source leaves a boundary unknown"}
    result = pipeline.gate({"run_id": "duplicate"}, "verify_batch", "revision", [item, item])
    assert len(store.get(result["issues_ref"])) == 1


@pytest.mark.parametrize("permanent", [False, True])
def test_comparison_identity_repairs_are_bounded(tmp_path, settings, store, permanent):
    def transform(stage, payload, result):
        if stage == "claims" and (permanent or not payload.get("feedback")):
            result.checked_ids = []
        return result

    model = FixtureModel(transform)
    with persistent_graph(Pipeline(settings, store, model)) as graph:
        result = graph.invoke(initial(tmp_path), config())
    assert result["status"] == ("review" if permanent else "complete")
    assert model.calls.count("claims") == (3 if permanent else 2)
    assert model.calls.count("extract") == 1
    if permanent:
        assert not result.get("bundle_ref")
