# Independent graph and documentation run debugger

## 1. Outcome and scope

Build an offline, read-only inspection application that explains what the pipeline found, how it used that knowledge, and where generated documentation lost support or coverage. Export a self-contained HTML application and a machine-readable JSON dataset from an existing run. Opening the application must require neither a running pipeline nor credentials, a model call, an Internet connection, or a separate frontend build system.

The application must provide both an exact view of the persisted knowledge graph and an end-to-end run inspector. A visually attractive sample of retrieved facts is insufficient: every stored node, edge, evidence record, and available stage revision must remain discoverable. Filters and neighborhood views may reduce what is drawn, but must always display visible and total counts and provide an explicit reset.

This plan is grounded in the current repository. Existing instrumentation should be reused before introducing new pipeline telemetry. Do not change extraction, generation, approvals, or graph semantics to implement the debugger. Do not add model calls or develop the Auggie integration. Spending remains an observable property of runs; the debugger introduces no spending policy.

## 2. Existing data and important constraints

| Source | Existing implementation | Inspector responsibility |
| --- | --- | --- |
| `runs/<run>/graph.sqlite` | `knowledge.py`: `nodes`, `edges`, `assertions`, `support`, `evidence`; optional `assertion_metadata`, `evidence_metadata`, `verified_relations`, graph metadata | Read every row, preserve identities, join enriched metadata without losing base fields, and identify missing tables in older runs. |
| `graphs/<revision>/graph.sqlite` and `manifest.json` | `Pipeline.finalize_graph()` | Offer explicitly labeled frozen graph revisions; never confuse them with the mutable current run graph. |
| Evidence revision packets and content-addressed objects | `RevisionEvidenceService`, `ArtifactStore` | Resolve the selected run's recorded evidence revisions, provenance, source snapshots, and approved knowledge deltas. Preserve separate source-snapshot, graph-revision, and evidence-revision identities. |
| `run-manifest.json` | `StageArtifacts.initialize()` | Obtain the run's historical step map and policy/runtime signature; do not assume the current `STEPS` list matches an old run. |
| `stepN/**/revisions/rNNNN/manifest.json` and `result.json` | `StageArtifacts.record()` | Index every item and revision, including full input/output state and referenced objects. Verify recorded hashes before presenting integrity as confirmed. |
| `events.jsonl` | `ArtifactStore.event()`, model and pipeline wrappers | Display requests, responses, cache hits, failures, completion durations, attempts, routes, and repairs in recorded order. |
| `checkpoints.sqlite` | LangGraph SQLite saver | Expose checkpoint identity, parent relationship, namespace, available timestamps/metadata, and recorded pending writes. Treat missing or undecodable history as unavailable, not an empty successful run. |
| `coverage.json`, `source-coverage.json`, `audit.json`, aspect and decision references | Source inventory, independent audits, documentation audit | Separate extraction coverage, source-aspect coverage, retrieval, fact utilization, final passage support, and unresolved attachments. |
| Candidate directories and release records | `export_candidate()`, `finalize_release()` | Browse candidate revisions, final Markdown, mappings, placements, citation occurrences, findings, approval decisions, and bundle integrity. |
| Shared ledger `charges` table | `budget.py` | Read only rows for the selected run, showing recorded usage, settled/uncertain/reserved charges and pricing provenance. Do not count stage/event summaries again. |

`KnowledgeGraph.__init__()` creates tables, `ArtifactStore.__init__()` creates directories, and `Pipeline` constructs a graph. The exporter must not instantiate these classes against inspection inputs. The current CLI loads model/runtime configuration before handling most commands. Dispatch the new inspection command before model initialization and independently of provider credentials and pricing validity.

The retrieval API intentionally limits optional context. Do not use `retrieve()` or a first page of `EvidenceService` search results as the graph export. The authoritative graph is the complete set of persisted rows.

Verified relations may contain several evidence IDs while `edges.evidence_id` stores only one. Display the original edge row and the complete verified relation payload separately; joining must not discard additional evidence. Exact-subject links and conflict candidates must retain their recorded method and uncertainty. A conflict candidate is not an independently confirmed contradiction.

## 3. Architecture and CLI

Implement a small `src/docgen_graph/inspection/` package with cohesive responsibilities:

- `reader.py`: safe read-only paths, SQLite readers, stage/event/object indexing, integrity diagnostics, and normalized export model.
- `export.py`: build a portable dataset and write the HTML/JSON bundle atomically using shared storage helpers.
- Packaged HTML, CSS, and JavaScript assets: render and navigate the exported dataset without external libraries or network requests.

Equivalent names are acceptable when they improve cohesion. Do not introduce a frontend server, package manager, graph database, or speculative plugin abstraction. A deterministic Canvas or SVG graph renderer plus accessible tables is sufficient. Include static resources in the Python wheel.

Add:

```text
docgen inspect-run --workspace <artifact-workspace> --thread-id <run-id> --output <directory>
docgen inspect-run --workspace <artifact-workspace> --thread-id <run-id> --output <directory> --ledger <ledger.sqlite>
```

`--workspace` should have the existing workspace default, while allowing a copied workspace to be inspected directly without a `.env` file. Explicit paths take precedence. `--ledger` is optional; missing cost data must not block graph inspection. Write `index.html` and `inspection.json`; print the absolute HTML path and an integrity/warning summary. Exit successfully for a usable partial run, but fail clearly for an invalid run identifier, nonexistent run, unreadable root, or unsafe output target. Reject output paths that overlap input run, object, graph, or checkpoint locations.

Do not automatically open a browser or start a pipeline. The application represents an export captured at a displayed time. Refresh means re-export; do not imply it is monitoring a live process.

## 4. Reader and export contract

Use a versioned JSON envelope containing `schema_version`, capture metadata, run identity, graph datasets/revisions, stage records, chronological events, checkpoint metadata, resolved artifacts, candidates, quality data, cost records, and diagnostics. Stable IDs and explicit references must allow any selected UI item to link to its source record. Preserve the complete source payload for detailed inspection after secret redaction.

1. Resolve and validate the workspace and run paths. Follow only declared artifact references and known run subdirectories, never recursively copy the whole workspace. Reject traversal, absolute references outside approved roots, and symlink escapes. Validate content-addressed keys as SHA-256 identifiers before reading object paths.
2. Open SQLite with `mode=ro` and `PRAGMA query_only=ON`. Use a read transaction or an in-memory SQLite backup for a consistent database snapshot. Never run schema setup, migrations, writes, checkpoints, or journal cleanup against input databases. Record export start/end times; files may change during export, so report mismatched hashes rather than claiming a transaction across all files.
3. Read all graph rows in deterministic order. Preserve disconnected nodes, parallel edge types/methods, self-links, unsupported assertions, and dangling endpoints as diagnostics. Never silently drop records because relationships are malformed.
4. Detect optional tables using `sqlite_master`; support legacy runs without enriched metadata. Merge base and enriched fields explicitly and report conflicts instead of silently overriding graph identity.
5. Index all stage items and revisions, including skipped and pending-review manifests. Preserve stage sequence separately from event chronology. Step numbers are identifiers, not execution order: recently added nodes have appended numbers and run earlier in the pipeline.
6. Resolve references reachable from stage inputs/outputs and revision packets with a visited set. Verify object hashes. Distinguish a missing object, a corrupted object, an unreadable binary object, and valid JSON. Avoid loops or duplicate object bodies. Binary attachments need metadata, locator, and a clear preview-unavailable state; generic binary rendering is not required.
7. Read JSONL events independently; retain valid records around malformed lines and report exact bad line numbers. A trailing partial line in an active run is a warning. Preserve duplicate events and retries instead of deduplicating by stage name.
8. Read checkpoint headers and safe JSON metadata directly. Do not instantiate `Pipeline`, deserialize arbitrary Python objects, enable pickle fallback, or execute imported types to inspect a checkpoint. If a checkpoint payload cannot be decoded safely, show its type/size and unavailable-detail reason. Full state is already available from immutable stage JSON. Pending writes must be marked as recorded data, not inferred task success.
9. Resolve current and historical candidate artifacts and graph/evidence revisions only when they belong to the selected run. Label associations as unavailable when no durable binding exists. Never assign a graph revision by filesystem modification time.
10. Build a diagnostic list with severity, source, affected IDs, and recovery explanation. Export incomplete data honestly. An empty graph from an early interrupted run must still produce a useful timeline and issue view.

## 5. Graph explorer

Provide a graph canvas, synchronized node/edge tables, search/filter controls, and a detail panel.

- Draw actual directed edges and identify stored edge type and method. Show a legend for node types and edge categories; preserve parallel edges in the edge list even where rendering overlaps.
- Fit, zoom, pan, select, reset, and focus a configurable one- or two-hop neighborhood. Keep deterministic placement so repeated inspections are comparable. Make disconnected components accessible.
- Search IDs, names, assertion statements, source paths, evidence text, categories, and provenance. Filter by node type, relation type/method, code/document/attachment origin, product category, relevance, temporal status, review status, and provider when those fields exist.
- Display exact loaded, matching, and currently drawn counts. Large graph rendering may use an explicitly labeled neighborhood or page, but the complete tables and search must remain accessible. No hidden hardcoded node cap or first-N-only export.
- Show assertion conditions/exceptions/modality; evidence locator, original text, source hash and snapshot; code history/diff-hunk side when present; provider/model, SDK/session/request IDs, verifier/review status, and linked relations/provenance.
- Selection should support incoming/outgoing edges, assertion-to-evidence traversal, and links to source aspects, retrieval packets, generation sections, and final passages that reference the selection.
- Keep stored graph edges and inspector-derived trace links separate in the dataset and UI. Derived links such as `used in section` or `mapped to passage` must identify the originating artifact and must never inflate stored graph edge counts.
- Let the user select the current graph or an available frozen graph revision. Show revision identities prominently and prevent references from a different revision being presented as confirmed matches.

## 6. Run, content, and quality inspector

Provide top-level Graph, Run, Content, and Quality views with persistent selection through URL fragments where practical.

### Run

Show chronological events alongside a step inventory. A selected stage exposes every item/revision, exact input/output JSON, route, attempts, repairs, issues, artifact references, and relevant model/tool activity. Display recorded duration and timestamps only where available. Show a structured before/after comparison for two revisions of the same stage item, including changed references and text fields.

Show checkpoint ID/parent/namespace and metadata as an independent history. Do not fabricate an exact stage-to-checkpoint association where the artifacts do not establish one. Human review states, rejection, unresolved issues, skipped stages, and recorded pending writes must be visibly distinct from completion.

Show model request/response/cache/error events and tool calls/results, including unavailable, unsupported, unresolved, and truncated outcomes. Show selected-run costs from the ledger, separating settled charges, uncertain charges, and active reservations; show token usage and pricing provenance where recorded. Never label cache hits as new calls or sum the same ledger charges with event/stage cost summaries.

### Content

Browse plan, section drafts, edited sections, and exported candidate versions from actual references. Present safe plain-text/Markdown source, with full JSON available, instead of evaluating arbitrary HTML or Mermaid from a run. Permit searching complete content and comparing draft/edit revisions. Candidate `audit.json` provides final mappings, placements, citations, and offsets: select a passage and follow it to facts and original evidence, and select a fact to find all mapped passages. Validate passage offsets against the exact candidate text before highlighting; show a mismatch instead of highlighting a wrong range.

### Quality

Provide independent counts and drill-down lists for:

- source spans represented, explicitly excluded, unresolved, or unavailable;
- inventoried source aspects and qualifiers, their audit decisions and unresolved items;
- graph facts retrieved, assigned, mapped into candidate passages, and unutilized;
- final source-to-document coverage, unsupported/missing mappings and citation findings;
- unresolved/conflicting facts, uncertain code analysis, unsupported attachments, template/numbering findings, and repetition findings already recorded by audits.

Always state each metric's denominator and source. A run using every graph fact does not establish that all relevant source knowledge was discovered. A missing source-aspect audit is `not available`, not zero omissions or 100% completeness. Respect the audit's recorded result, including an empty inventory, without upgrading it into an independent quality guarantee.

## 7. Offline safety and portability

The viewer must never execute source code, generated HTML, SVG, Mermaid, scripts, model prompts, or checkpoint objects. Render untrusted content with `textContent` or correctly escaped markup. Embed JSON safely against `</script>` and Unicode separator injection; a non-executable encoded payload is acceptable. Use a restrictive Content Security Policy, disable network fetching, and ship all assets locally or inline. External source URLs should be inert text or explicit user-clicked safe HTTP(S) links; block executable URL schemes.

Never export `.env`, authentication files, full process environment, SDK private homes, or unrelated workspace files. Recursively redact credential fields and common bearer/API token formats from events, state, prompts, and source excerpts before producing HTML/JSON. Record redaction counts without exposing removed values. Treat the export as containing project source/documentation; sanitization prevents credential leakage but does not make it a public document. No telemetry or third-party assets.

Keep Windows paths, spaces, non-ASCII names, and `file://` opening functional. The single HTML file must work when moved away from the source workspace; JSON is a companion export, not a runtime fetch dependency.

## 8. Implementation sequence and ownership

1. Implement the normalized reader/export contract and diagnostics using small temporary fixtures for legacy, current, and interrupted runs. Verify exact graph identity/counts and all stage revisions before building UI.
2. Add the isolated `inspect-run` CLI branch and packaged static assets. Keep changes to `cli.py` narrow because another agent is exercising live Codex flows. Coordinate before changing shared configuration or model code; those changes should not be needed.
3. Build graph selection, searchable tables, details/evidence traversal, and full-count indicators.
4. Add stage timeline/revision comparison, checkpoint metadata, model/tool events and costs, content traceability, and quality drill-downs.
5. Add safety/portability checks, real-run export, browser verification, README usage, and an implementation report recording supported data and remaining limitations.

The implementer owns `inspection/`, `tests/test_inspection.py`, CLI integration, README usage, and `evaluation/graph-debugger/implementation-report.md`. The planner owns this document. The live-run agent owns its run inputs/artifacts and Codex integration fixes. The exporter must be able to inspect that run once artifacts exist without changing its execution.

## 9. Verification and completion criteria

Use offline fixtures and recorded runs; no additional model calls are needed to test the debugger.

- Compare every exported stored node and edge identity with SQL rows, including a fixture larger than the initial display page, disconnected nodes, multiple relation methods, and verified relations with multiple evidence IDs. Confirm every record can be found after resetting filters.
- Verify legacy missing metadata, partial pre-graph runs, missing/corrupt objects, malformed/trailing JSONL, interrupted/pending checkpoints, missing ledgers, and multiple stage/candidate revisions produce useful diagnostics and no fabricated success.
- Assert input file hashes and modification timestamps remain unchanged, no database or directory is created for a missing input, and no `Pipeline`, `GeminiModel`, network client, or paid-call factory is constructed by the CLI command.
- Exercise traversal/symlink escape, malicious artifact names, script-ending strings, executable URL schemes, credential sentinels, and unsafe checkpoint payloads. Assert secrets and executable source markup do not appear in output behavior.
- Verify passage-to-fact-to-evidence navigation, reverse utilization lookup, denominator separation, revision comparison, mismatched offsets, and uncertain/reserved cost handling without double counting.
- Export a real existing run and the current Codex-backed run when available. Check the browser offline: initial render without console errors, graph search/filter/select/reset, evidence details, timeline/revision selection, candidate passages, quality drill-down, and a moved standalone HTML file. Record actual tested commands, fixture sizes, browser checks, and limitations in the implementation report.
- Run relevant tests, Ruff, and packaging verification. Confirm the built wheel contains viewer resources. Keep the full existing test suite green.

Completion requires an independently usable exported application, not only JSON, a screenshot, a proposed UI, or a notebook. Missing telemetry in historical runs is an explicitly labeled limitation; it must not block inspection of the data that exists. Additional pipeline instrumentation, automatic refresh, a server, and multi-user editing are outside this implementation.
