# Independent graph and run inspector implementation

## Delivered behavior

`docgen inspect-run` exports `index.html` and `inspection.json` from a recorded workspace. The command branches before `Settings.load()` and never constructs the pipeline, a model client, an artifact store against the input, or a writable knowledge graph. It works with copied workspaces and no `.env`. An optional explicit ledger contributes only charges belonging to the selected run.

The HTML contains its dataset, styles, and JavaScript. No frontend runtime dependency, network request, telemetry, model call, server, or browser launch is part of the export. Source Markdown, HTML, SVG, Mermaid, and prompts remain inert text. A hash-based Content Security Policy blocks external resources. Known credential fields and common credential string formats are redacted; the export still contains private project material.

Graph preserves every SQL node and edge, disconnected records, parallel edge methods, self-links, unsupported facts, original evidence, enriched metadata, and complete verified relation evidence IDs. It provides current/frozen revision selection, search, filters, directed edges, zoom/pan/fit, one/two-hop neighborhoods, selection, evidence traversal, and paginated complete tables. Drawing uses an explicitly counted 75-node page. Provider metadata can be joined by recorded provenance IDs to reachable revision artifacts when it is not in the graph database. Legacy document/code origin is available through the recorded evidence kind. No provider is inferred when provenance is absent.

Run includes historical stage inventory, skipped/pending manifests, every item/revision, exact input/output state, revision differences, events in recorded line order, checkpoint headers, opaque binary payload descriptions, recorded pending writes, and selected-run settled/uncertain/reserved charges. Stage numbers are displayed as historical identifiers in numeric order, not claimed execution order. Stage-name event associations and unavailable checkpoint-to-stage associations are explicit.

Content browses reachable artifacts and all candidate-manifest files. Candidate passages validate Unicode code-point offsets against the exact exported candidate text before highlighting. Fact navigation uses the candidate's recorded frozen graph revision. Quality separates recorded source discovery/audits from graph retrieval, section assignment, and candidate utilization. Derived metrics include their source records and denominators. Missing audits and unbound graph revisions remain unavailable.

## Input integrity

The reader only follows known run directories, candidate manifests, recorded graph revisions, and validated content-addressed references. Traversal and symlink escapes are rejected. Candidate paths remain confined to their candidate directory; authentication/configuration filenames are blocked case-insensitively. Shared objects are read once per export.

SQLite databases and existing WAL/SHM sidecars are copied to temporary snapshots, checked for concurrent byte changes, and opened with `mode=ro` plus `query_only`. Inputs are never opened for database writes or migrations. Object, stage result, logical stage content, and candidate file hashes are checked before redaction. Malformed JSONL lines preserve valid surrounding events. Missing/corrupt objects and malformed candidate structures retain diagnostics and available raw data.

## Verification

Targeted command:

```powershell
.venv/Scripts/python.exe -m pytest tests/test_inspection.py --basetemp .docgen/inspect-tests6 -q
```

Result: 17 tests passed. Fixtures cover 203 nodes, parallel edges, a self-link, a dangling endpoint, JSON-looking original source text, multiple stage revisions, pending/skipped stages, malformed JSONL, missing/corrupt artifacts, malicious candidate paths, an actual symlink escape, credential redaction, script-ending source strings, CSP hashes, non-ASCII paths, checkpoint bytes, ledger scoping, Unicode passage offsets, revision-bound utilization, and malformed audit structures. A WAL fixture confirms uncheckpointed rows remain visible while every input file's bytes and modification timestamp remain unchanged. The CLI test rejects any attempted settings/model/pipeline initialization.

The coordinating agent ran the integrated suite before the final malformed-audit regression: 165 tests passed. Ruff and `node --check src/docgen_graph/inspection/viewer.js` passed. `uv build --offline --cache-dir .docgen/uv-cache` produced the source distribution and wheel; the wheel contains the reader, exporter, quality module, and all three viewer assets. A one-off Prettier invocation formatted static sources without adding project dependencies.

Completed offline fixture export:

```powershell
docgen inspect-run --workspace .docgen/final34/test_autopilot_reaches_release0/runtime --thread-id example --output .docgen/inspection-demo
```

This captured two graph datasets of 4 nodes / 3 edges each, 37 stage revisions, 37 events, 37 resolved objects, 74 checkpoints, and one candidate. Its only diagnostic is the deliberately omitted optional ledger.

Actual Codex-backed interrupted-run export:

```powershell
docgen inspect-run --workspace .docgen/codex-live-validation --thread-id codex-risk-live-20261012-d --output .docgen/inspection-live-d --ledger .docgen/budget.sqlite
```

This captured current and frozen graphs of 218 nodes / 237 edges each, 25 stage revisions, 56 events, 72 reachable objects, and 15 ledger rows. The run stopped after graph construction; the inspector does not imply that documentation completed. Newer live-run exports can use the same command with their run ID.

The coordinating agent checked the exported application in a browser using an isolated local preview: graph filtering, node/evidence selection, frozen graph selection, fact-to-passage-to-fact traversal, verified passage offsets, 67 stage inventory/revision records, revision comparison, and quality denominators. No browser errors were reported. Direct `file://` navigation is unavailable in the browser automation environment; it was not bypassed. Self-contained payload and CSP tests confirm the HTML does not fetch its companion JSON or any external resource.

## Explicit limitations

- Checkpoint binary serialization is deliberately not deserialized. Full immutable stage state is available separately.
- Binary attachments have size/hash metadata and an unavailable-preview message. No OCR, binary document rendering, or source code execution is introduced.
- Historical missing provenance, missing audits, unsupported schemas, and absent durable associations cannot be reconstructed accurately and remain unavailable.
- Files across a workspace are not one atomic transaction. Capture timestamps and hash mismatches disclose concurrent changes; database snapshots protect each database independently.
- Secret redaction is a conservative pattern-based safeguard, not a claim that an arbitrary project export is safe to publish.
- The application is a captured offline inspector. Re-exporting is required to see later pipeline activity.
