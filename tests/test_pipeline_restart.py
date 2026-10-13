import re
import shutil
import sqlite3
from contextlib import closing
from pathlib import Path

from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.types import Command

from docgen_graph.storage import ArtifactStore
from docgen_graph.workflow import Pipeline


class FixtureModel:
    def __init__(self):
        self.calls = []

    def call(self, stage, payload, schema=None):
        self.calls.append(stage)
        if stage == "locate_visual_evidence":
            spans = {item["id"]: item for item in payload["original_evidence"]}
            return {
                "locations": [
                    {"support_id": item["support_id"], "quote": spans[item["evidence_id"]]["text"]}
                    for item in payload["required_support"]
                ]
            }
        if stage == "inventory_aspects":
            return {
                "aspects": [
                    {
                        "evidence_id": block["id"],
                        "quote": block["text"],
                        "kind": "obligation",
                        "description": block["text"],
                    }
                    for block in payload["blocks"]
                ],
                "non_substantive": [],
            }
        if stage in {"audit_source_coverage", "audit_source_to_document"}:
            return {
                "decisions": [
                    {
                        "aspect_id": aspect["id"],
                        "fact_ids": [
                            fact["id"]
                            for fact in payload["facts"]
                            if aspect["evidence_id"] in fact["evidence_ids"]
                        ],
                        "status": "represented",
                        "reason": "Fixture retains the exact source text",
                    }
                    for aspect in payload["aspects"]
                ],
                "findings": [],
            }
        if stage == "extract_document":
            return {
                "assertions": [
                    {
                        "statement": re.sub(r"!\[([^]]+)\]\([^)]+\)", r"\1", block["text"])
                        .lstrip("# ")
                        .replace("\r\n", "\n"),
                        "subject": "return_value",
                        "predicate": "describes",
                        "evidence_ids": [block["id"]],
                    }
                    for block in payload["blocks"]
                ],
                "excluded": [],
            }
        if stage == "semantic_graph":
            return self.semantic_graph(payload)
        if stage == "audit_semantic_graph":
            return {
                "accepted": True,
                "findings": [],
                "covered_obligation_ids": [fact["id"] for fact in payload["facts"]],
            }
        if stage == "draft_plan":
            groups = payload["groups"]
            headings = payload["template_headings"]
            return {
                "title": "Example",
                "sections": [
                    {
                        "title": heading,
                        "purpose": "Explain supported behavior",
                        "group_ids": [group["id"] for group in groups] if index == 0 else [],
                        "support_group_ids": []
                        if index == 0
                        else [group["id"] for group in groups],
                        "queries": ["return_value"],
                    }
                    for index, heading in enumerate(headings)
                ],
                "unknowns": [],
                "discrepancies": [],
                "exclusions": [],
            }
        if stage == "write_section":
            original = {item["id"]: item for item in payload["original_evidence"]}
            assertions = payload["assertions"] or payload["supporting_assertions"]
            mappings = []
            lines = []
            for item in assertions:
                label = original[item["evidence_ids"][0]]["label"]
                role = "Code" if label.startswith("C") else "Legacy"
                statement = item["statement"].replace("\r\n", "\n")
                lines.append(f"{statement} [{role} {label}]")
                if payload["mandatory_obligation_ids"]:
                    mappings.append(
                        {
                            "obligation_id": item["id"],
                            "citation_ids": [label],
                            "passage": lines[-1],
                            "support_quotes": {label: original[item["evidence_ids"][0]]["text"]},
                        }
                    )
            return {"markdown": "\n\n".join(lines), "mappings": mappings}
        if stage == "verify_section":
            return {
                "accepted": True,
                "findings": [],
                "covered_obligation_ids": [item["id"] for item in payload["assertions"]],
            }
        if stage == "edit_page":
            return {"markdown": payload["markdown"]}
        return {"accepted": True, "findings": []}

    def semantic_graph(self, payload):
        sources = {source["id"]: source for source in payload["sources"]}
        topics = {}
        rules = []
        for fact in payload["facts"]:
            quotes = [
                {
                    "evidence_id": identifier,
                    "start": 0,
                    "end": len(sources[identifier]["text"]),
                    "text": sources[identifier]["text"],
                }
                for identifier in fact["evidence_ids"]
            ]
            topic_key = f"{fact['scope']}:{fact['subject']}"
            topic = topics.setdefault(
                topic_key,
                {
                    "key": topic_key,
                    "name": fact["subject"],
                    "scope": fact["scope"],
                    "quotes": [],
                },
            )
            topic["quotes"].extend(quotes)
            rules.append(
                {
                    "key": fact["id"],
                    "topic_key": topic_key,
                    "statement": fact["statement"],
                    "scope": fact["scope"],
                    "modality": fact["modality"]
                    if fact["modality"]
                    in {"necessary", "sufficient", "necessary_and_sufficient", "prohibited"}
                    else "descriptive",
                    "fact_ids": [fact["id"]],
                    "quotes": quotes,
                    "topic_quotes": quotes,
                    "condition_groups": [
                        {
                            "operator": "unspecified",
                            "quotes": quotes,
                            "conditions": [
                                {"statement": item, "quotes": quotes} for item in fact["conditions"]
                            ],
                        }
                    ]
                    if fact["conditions"]
                    else [],
                    "exceptions": [
                        {"statement": item, "quotes": quotes} for item in fact["exceptions"]
                    ],
                }
            )
        return {"topics": list(topics.values()), "rules": rules, "findings": []}

    def tool_turn(self, payload, messages, declarations):
        self.calls.append("authoring_action")
        return {
            "content": {
                "role": "model",
                "parts": [{"text": "Required fixture evidence is available."}],
            },
            "calls": [],
        }


def build(tmp_path: Path, model: FixtureModel):
    store = ArtifactStore(tmp_path / "runtime")
    connection = sqlite3.connect(store.root / "checkpoints.sqlite", check_same_thread=False)
    graph = Pipeline(store, model, "test-run").build(SqliteSaver(connection))
    return store, connection, graph


def test_shared_fixture_model_supports_graph_only_pipeline(tmp_path):
    document = tmp_path / "guide.md"
    document.write_text("# Guide\n\nReturn the supplied value.\n", encoding="utf-8")
    model = FixtureModel()
    store, connection, graph = build(tmp_path, model)
    with closing(connection):
        result = graph.invoke(
            {
                "run_id": "test-run",
                "docs": str(document),
                "graph_only": True,
                "brief": "",
                "mode": "autopilot",
            },
            {"configurable": {"thread_id": "test-run"}, "recursion_limit": 150},
        )
    assert result["status"] == "graph_complete"
    assert "semantic_graph" in model.calls
    assert "audit_semantic_graph" in model.calls
    assert not {"draft_plan", "write_section", "edit_page"}.intersection(model.calls)
    assert (store.root / "runs" / "test-run" / "graph-quality.json").is_file()


def test_plan_and_release_require_exact_review_across_restarts(tmp_path):
    docs = tmp_path / "docs"
    docs.mkdir()
    (docs / "guide.md").write_text("# Guide\n\nReturn the supplied value.\n", encoding="utf-8")
    template = tmp_path / "template.md"
    template.write_text("## Behavior\n\n## Sources\n", encoding="utf-8")
    model = FixtureModel()
    config = {"configurable": {"thread_id": "test-run"}}
    store, connection, graph = build(tmp_path, model)
    with closing(connection):
        graph.invoke(
            {
                "run_id": "test-run",
                "docs": str(docs),
                "template": str(template),
                "brief": "",
                "status": "running",
            },
            config,
        )
        state = graph.get_state(config)
        assert state.values["status"] == "awaiting_plan_review"
        assert "write_section" not in model.calls
        plan_hash = state.values["plan_hash"]
        assert state.tasks[0].interrupts[0].value["plan_hash"] == plan_hash
        frozen = store.root / "graphs" / state.values["graph_revision"] / "graph.sqlite"
        with sqlite3.connect(frozen) as graph_connection:
            assert graph_connection.execute("SELECT COUNT(*) FROM assertions").fetchone()[0] > 0

    _, connection, graph = build(tmp_path, model)
    with closing(connection):
        graph.invoke(
            Command(
                resume={
                    "action": "approve_plan",
                    "plan_hash": "stale",
                    "reviewer": "Tester",
                    "rationale": "Checked",
                }
            ),
            config,
        )
        state = graph.get_state(config)
        assert state.values["status"] == "awaiting_plan_review"
        graph.invoke(
            Command(
                resume={
                    "action": "approve_plan",
                    "plan_hash": plan_hash,
                    "reviewer": "Tester",
                    "rationale": "Checked",
                }
            ),
            config,
        )
        state = graph.get_state(config)
        assert state.values["status"] == "ready_for_review"
        candidate = state.values["candidate_ref"]
        assert (
            store.root
            / "runs"
            / "test-run"
            / "candidates"
            / candidate
            / "documentation"
            / "index.md"
        ).is_file()
        assert state.tasks[0].interrupts[0].value["candidate_hash"] == candidate
        exported = store.root / "runs" / "test-run" / "candidates" / candidate
        copied = tmp_path / "portable"
        shutil.copytree(exported, copied)
        for page in copied.rglob("*.md"):
            for link in re.findall(r"\]\(([^)]+\.md)\)", page.read_text("utf-8")):
                assert (page.parent / link).resolve().is_file()

    _, connection, graph = build(tmp_path, model)
    with closing(connection):
        graph.invoke(
            Command(
                resume={
                    "action": "approve_release",
                    "candidate_hash": candidate,
                    "reviewer": "Tester",
                    "rationale": "Checked",
                }
            ),
            config,
        )
        assert graph.get_state(config).values["status"] == "complete"
        assert (store.root / "runs" / "test-run" / "releases" / f"{candidate}.json").is_file()
