# Task IV implementation report

Date: 2026-10-12. Baseline: `1d96d0af`. Implementation was developed in the
`codex/task-4-documentation` worktree in parallel with Task III and integrated
through its C0, C1, C2, C3, and final producer commits. No historical generated
fixture or oracle was relabeled as human reviewed.

## Observation and implementation matrix

| Observation | Baseline assessment | Implemented behavior |
| --- | --- | --- |
| Humanization | Existing writer/editor already supported grouped facts and local rewriting | Reader-oriented prompts explain prerequisites, behavior, outcomes and only documented rationale; independent editing audit receives explicit qualifier/causality risks |
| Exact evidence after rewriting | Substantially present | Existing mappings, source quotes, placement offsets and bundle checks retained; new knowledge requires separately audited immutable revision and invalidates plan/release approval |
| All graph nodes used but original details absent | Confirmed design gap; no specific last-run ID supplied | Independent original-source aspect inventory, source-to-fact audit, and final source-to-passage audit; missing-condition integration test blocks before planning despite a fact for every source block |
| Agentic authoring | Missing explicit function loop | Real Gemini function declarations with automatic execution disabled; persistent plan/execute/verify nodes during planning and section preparation, bounded turns/time/bytes and repeat detection |
| Mermaid tools | Renderer and semantic checks already existed | Executable diagram tool builds validated Mermaid source with an independent audit requiring every node/edge ID; the existing publication renderer handles output; endpoints alone do not justify an edge |
| Attachments | Static image handling existed; general text absent | Local TXT/MD, PDF, DOCX, CSV, XLSX parsers and source registers integrated with Task III snapshot/graph; native citation coordinates and frozen resource export |
| Template numbering | Flat heading requirement model | Markdown heading tree, stable structural IDs, repeated dynamic slots, fixed-number conflicts, nested generated numbers and local anchor updates |
| Working title “Plan” | Exact offending run unavailable; narrow validator reproduced | Explicit template title preferred; generic documentation/working/Polish plan titles repaired while Pricing Plan and Disaster Recovery Plan remain valid |
| Repetition | Exact long paragraph detection existed | Near-duplicate paragraph/table candidates independently audited before bounded editing; different scopes/conditions remain separate |
| Automatic exclusion | Confirmed complete-with-exclusions bypass | Exhausted substantive repairs end `incomplete`; both old missing-span and single-span automatic exclusion branches removed |

## Persistence and shared contracts

Existing step1–step27 retain their identifiers. Appended stages cover original
aspect inventory, source discovery audit, authoring actions and tool results,
final source audit, verified delta publication, and Task III code scope and
classification. Every stage writes its artifact through the existing store and
LangGraph SQLite checkpoint. Runtime signatures recursively hash subpackages,
prompts and effective provider/tool configuration.

Task III's evidence service binds queries to snapshot, graph revision and scope.
Source aspects are converted to its coverage records. Actual provider provenance
survives publication. Tool-discovered new facts require an independent Gemini
audit of exact delta bytes; graph evidence is synchronized before assertions,
the inventory and provenance are extended, and approvals/content are cleared
before plan revalidation.

Authoring persists full SDK Content JSON rather than reconstructing calls from
names. Binary thought signatures therefore retain the SDK's base64 encoding.
Every tool-planning turn and independent semantic audit uses the same Gemini
budget/cache/retry implementation as ordinary stages.

## Regressions and verification

Added tests cover source condition loss, protected values and invented causes,
numbering 3.1/3.2/3.3 and 3.2.1, fixed-number conflicts, optional/dynamic slots,
stable heading IDs, generated anchor rewriting without changing fenced code,
title exceptions, CSV/DOCX locators, unreadable/scanned content, XLSX formulas
without cached values, and attachment content reaching the publication bundle.

The integration tests inject crashes before tool execution, after execution
before verification, and before final source auditing. Reopening the persistent
graph resumes the saved protocol and completes the exact evidence-mapped
fixture. Protocol and coordinator review tests also cover SDK thought-signature
roundtrip, code-provider isolation/accounting boundaries, and a Mermaid tool
request that must reject an edge omitted from the independent audit.

Completed offline checkpoints: 116/119 tests before the final optional-heading
fix and LF fixture normalization; the three failures were that heading decision
and two physical Windows CRLF hashes for the declared-LF producer fixture.
After fixes, the targeted attachment, numbering, evidence-contract, and tool
integration suite passed 19/19. The parent integration run records final suite
totals after all producer and reviewer changes. Long Windows temporary paths
caused four earlier visual-bundle failures; rerunning under a short repository
temporary path passed those unchanged regressions.

Final root integration validation: the complete suite passed 143/143 tests
(`pytest -q --basetemp=.docgen/final34`). A subsequent direct Mermaid tool
regression exposed and corrected a missing diagram ID; both new cases pass,
including rejection when the edge is absent from the independent audit. All
12 coordinator review tests then passed. This verifies 145 distinct current
test cases across the full run and the focused follow-up. Ruff passed across
`src` and `tests`; the final wheel built successfully and CLI help exposes both
provider-selection flags. The shared ledger was reread and remained unchanged.

No paid model call was made. Existing ledger figures were PLN 445.4719064244
charged plus PLN 1.62453494619 reserved against PLN 200 authorization. Accounting
was not reset or bypassed.

## Limits and remaining acceptance

- Live Gemini function calling and SDK service behavior require later paid
  validation under an explicitly authorized budget. Offline tests verify
  protocol, dispatch, accounting and persistence with controlled responses.
- Native Auggie remains explicitly unsupported where read-only host isolation
  cannot be verified. Provider selection is implemented without a silent
  fallback or an unsafe prompt-only sandbox.
- Model-based source and entailment audits can still miss information. Tests
  intentionally hold the omitted condition outside the extractor response;
  they do not prove completeness of an unannotated real corpus.
- Readability 4/5 human acceptance, live golden-document comparisons, and actual
  Mermaid browser/parser visual acceptance have not been performed. Existing
  deterministic renderer and evidence regressions are not represented as those
  acceptance results.
- Unsupported attachment interpretation requires a source-attributed transcript
  in a new source snapshot/run. Existing review cannot make missing pixels or
  uncached formula values evidentiary. Complex DOCX/PDF content stays visibly
  unresolved instead of being silently discarded.
