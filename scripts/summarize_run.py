"""Summarize saved run artifacts without verifying, mutating or calling the model."""

import argparse
import json
import re
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path


def read(path):
    return json.loads(path.read_text("utf-8"))


def seeded_conflicts(graph, spans):
    sections = {}
    for span in spans.values():
        match = re.search(r"Conflict group:\s*(CG-\d+)", span["excerpt"])
        if match:
            sections[(span["path"], tuple(span["headings"]))] = match[1]
    evidence = {e["id"]: e for e in graph.get("evidence", [])}
    claim_sections = {}
    for claim in graph.get("claims", []):
        found = defaultdict(set)
        for eid in claim["evidence_ids"]:
            span = spans.get(evidence[eid].get("span_id"))
            if span:
                for depth in range(1, len(span["headings"]) + 1):
                    section = (span["path"], tuple(span["headings"][:depth]))
                    if section in sections:
                        found[sections[section]].add(section)
        claim_sections[claim["id"]] = found
    matched = defaultdict(list)
    for conflict in graph.get("conflicts", []):
        found = defaultdict(set)
        for cid in conflict["claim_ids"]:
            for group, values in claim_sections[cid].items():
                found[group].update(values)
        for group, values in found.items():
            if len(values) >= 2:
                matched[group].append(conflict["id"])
    return {group: matched[group] for group in sorted(set(sections.values()))}


def summarize(root):
    manifest = read(root / "manifest.json")
    outputs = {}
    stages = {}
    processing_seconds = 0.0
    to_review_seconds = None
    for name, stage in manifest["stages"].items():
        active = next((a for a in stage["attempts"] if a["id"] == stage["active"]), None)
        stages[name] = {"status": stage["status"], "attempts": len(stage["attempts"])}
        for attempt in stage["attempts"]:
            if attempt.get("ended_at") and not name.startswith("review_"):
                processing_seconds += (
                    datetime.fromisoformat(attempt["ended_at"])
                    - datetime.fromisoformat(attempt["started_at"])
                ).total_seconds()
        if name == "review_knowledge" and active:
            to_review_seconds = round(
                (
                    datetime.fromisoformat(active["started_at"])
                    - datetime.fromisoformat(manifest["created_at"])
                ).total_seconds(),
                2,
            )
        if active and active.get("ended_at"):
            stages[name]["active_seconds"] = round(
                (
                    datetime.fromisoformat(active["ended_at"])
                    - datetime.fromisoformat(active["started_at"])
                ).total_seconds(),
                2,
            )
        if active and active["status"] == "completed":
            outputs[name] = read(
                root / "stages" / name / "attempts" / str(active["id"]) / "output.json"
            )
    calls = defaultdict(
        lambda: Counter(calls=0, input_tokens=0, output_tokens=0, reasoning_tokens=0)
    )
    for path in root.glob("stages/*/attempts/*/model-calls/*/request.json"):
        request = read(path)
        item = calls[request["prompt_id"]]
        item["calls"] += 1
        context = json.loads(request["variables"]["context"])
        item["repair_calls"] += int(
            "previous_resolution" in context or request["prompt_id"] == "repair_extraction"
        )
        item["max_context_chars"] = max(
            item["max_context_chars"], len(request["variables"]["context"])
        )
        response = path.with_name("response.json")
        if response.exists():
            usage = read(response).get("usage_metadata") or {}
            item["input_tokens"] += usage.get("input_tokens", 0)
            item["output_tokens"] += usage.get("output_tokens", 0)
            item["reasoning_tokens"] += usage.get("output_token_details", {}).get("reasoning", 0)
    graph = outputs.get("reconcile", outputs.get("extract", {}))
    graph_state = "reconciled" if "reconcile" in outputs else "extracted"
    if not graph:
        active_id = manifest["stages"]["extract"]["active"]
        partial = root / "stages/extract/attempts" / str(active_id) / "partial.json"
        graph = read(partial) if partial.exists() else {}
        graph_state = "partial_extraction" if graph else "absent"
    events_path = root / "events.jsonl"
    events = (
        [json.loads(line) for line in events_path.read_text("utf-8").splitlines()]
        if events_path.exists()
        else []
    )
    extraction_events = [e for e in events if e["event"] == "extraction_batch"]
    progress = extraction_events[-1] if extraction_events else None
    model_errors = [
        {"path": p.relative_to(root).as_posix(), "error": read(p)}
        for p in sorted(root.glob("stages/*/attempts/*/model-calls/*/error.json"))
    ]
    parsed = outputs.get("parse", {})
    spans = {s["id"]: s for s in parsed.get("spans", [])}
    names = Counter(e["name"].casefold().strip() for e in graph.get("entities", []))
    suspicious = [
        e for e in graph.get("entities", []) if re.search(r"CONF-SYNTH|^F-\d", e["version"])
    ]
    errors = [
        {"path": p.relative_to(root).as_posix(), "error": read(p)}
        for p in sorted(root.glob("stages/*/attempts/*/error.json"))
    ]
    return {
        "run_id": manifest["run_id"],
        "status": manifest["status"],
        "source": manifest["source"],
        "created_at": manifest["created_at"],
        "to_knowledge_review_seconds": to_review_seconds,
        "total_attempt_processing_seconds": round(processing_seconds, 2),
        "usage": manifest["usage"],
        "stages": stages,
        "model_calls": dict(calls),
        "stage_errors": errors,
        "model_errors": model_errors,
        "graph_state": graph_state,
        "extraction_progress": progress,
        "documents": [
            {k: d[k] for k in ("path", "content_hash")} for d in parsed.get("documents", [])
        ],
        "source_spans": dict(Counter(s["path"] for s in spans.values())),
        "table_rows": sum(max(0, len(s["table"]) - 1) for s in spans.values()),
        "graph": {
            k: len(graph.get(k, []))
            for k in ("entities", "claims", "relationships", "aliases", "conflicts", "evidence")
        },
        "coverage": dict(Counter(c["disposition"] for c in graph.get("coverage", []))),
        "processed_source_spans": dict(
            Counter(
                spans[eid]["path"]
                for eid in {r["evidence_id"] for r in graph.get("coverage", [])}
                if eid in spans
            )
        ),
        "excluded_kinds": dict(
            Counter(
                spans[c["evidence_id"]]["kind"]
                for c in graph.get("coverage", [])
                if c["disposition"] == "excluded" and c["evidence_id"] in spans
            )
        ),
        "duplicate_name_excess": sum(n - 1 for n in names.values()),
        "possible_page_ids_in_entity_version": len(suspicious),
        "review_gaps": graph.get("gaps", []),
        "version_examples": [
            {k: e[k] for k in ("id", "name", "type", "version")} for e in suspicious[:5]
        ],
        "conflicts": graph.get("conflicts", []),
        "seeded_conflict_groups_linked_across_sections": seeded_conflicts(graph, spans),
        "seeded_requirement_fragments": [
            {
                "path": span["path"],
                "start_line": span["start_line"],
                "claim_ids": [
                    c["id"] for c in graph.get("claims", []) if span["id"] in c["evidence_ids"]
                ],
            }
            for span in spans.values()
            if span["excerpt"].startswith("This section requires:")
        ],
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = json.dumps(summarize(args.run), ensure_ascii=False, indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(result + "\n", encoding="utf-8")
    else:
        print(result)
