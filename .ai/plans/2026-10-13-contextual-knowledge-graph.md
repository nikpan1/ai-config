# Context-preserving knowledge graph implementation

Status: written before implementation on 2026-10-13; implemented and graph-only evaluation passed.

## Objective

Build a source-grounded graph that preserves stories and exposes recurring business topics, rules, conditions and exceptions. Validate graph construction only; do not execute documentation planning, writing, editing or publishing during this work.

## Current limitations

- The line-based Markdown reader mistakes fenced headings for document headings, mishandles skipped heading levels and Setext headings, and can split a story across unrelated extraction calls.
- Extraction and its audits see the same context-limited batches. Block accounting alone cannot prove semantic preservation.
- Existing assertions retain conditions and exceptions as text fields, but recurring topics and rule logic are not explicit graph structures.
- The graph must retain exact source bytes and locations independently from display labels, semantic identities and formatting.
- `.ai/development-plan.md`, referenced by AGENTS.md, is absent in the current checkout. Preserve the provenance and coverage requirements already established in this conversation; this plan does not silently replace that missing file.

## Design decisions

1. Parse Markdown structure deterministically using the installed Markdown parser. Model-driven chunking is not the default: exact source ranges, reproducibility and format handling belong to the parser. Gemini 3.5 Flash-Lite is an optional user-authorized future experiment, not a substitute for the configured extraction/audit model. Keep `gemini-3.8-flash` for semantic work and preserve the model allowlist.
2. Keep immutable source fragments and their raw text, hashes and locations. Preserve heading ancestry, list/table/fence structure and story membership. Do not rewrite source text to make quotations match.
3. Separate owned extraction blocks from contextual blocks. Each substantive block is owned once; a story may be included as context in multiple requests. Context evidence retains its original identity and cannot silently acquire duplicate coverage ownership.
4. Preserve complete story context within bounded requests. Oversized stories must have explicit split/context accounting; never silently trim prerequisites, exceptions or unresolved cross-references. If a required context cannot fit, fail with a readable issue rather than continue with misleading completeness.
5. Preserve existing Assertion and SourceSpan records. Add explicit Topic and Rule structures, with Condition and Exception nodes tied to the owning rule. A shared topic connects repeated discussion across stories. Rule logic distinguishes conjunction, alternatives and unspecified relationships; necessary requirements must not become sufficient guarantees.
6. Semantic extraction proposes canonical topics and scoped relations against a reusable topic register. Independent verification must reject unsupported relationships, incorrect scope merges and missing qualifications. Ambiguity remains unresolved rather than being auto-merged through string similarity.
7. Every semantic node and relation must resolve to existing source evidence and exact quotations. Store quote-relative character positions and original source locations, including multi-fragment support. Keep all evidence when topics recur.
8. Keep LangGraph stages sequential and checkpointed with stable thread IDs. Use the existing interrupt/resume mechanism and shared accounting. Separate semantic proposal, audit and publication so a restart does not repeat completed model calls.
9. Provide an explicit graph-only execution mode that stops after a validated frozen graph and quality report. It must not call any documentation-generation stages.

## Work packages

### A. Structural parsing and story context

- Replace the ad hoc Markdown splitter with mapped syntax blocks, including ATX/Setext headings, correct ancestry, lists, tables and fenced blocks.
- Split long source text using exact offsets without losing bytes or inventing source content.
- Build a story register and owned/context batch records. Include context in aspect inventory, fact extraction and both source audits.
- Preserve existing evidence fields needed by downstream readers and historical inspection.

### B. Semantic graph and source citations

- Add strict contracts for topic assignments, rules, logical condition groups, exceptions and exact evidence quotations.
- Normalize semantic identities separately from source identities. Reuse canonical topics across repeated mentions while retaining scope distinctions and evidence union.
- Validate references, quote bounds, qualifiers, relation endpoints, source ownership and complete fact allocation before publication.
- Store semantic nodes, edges and evidence mappings in SQLite, expose them in the inspector, and make their original facts/evidence retrievable for later documentation use.
- Preserve legacy graphs and reject incompatible runtime resumes instead of rewriting old artifacts.

### C. Pipeline integration

- Add named checkpointed stages for semantic graph proposal, independent verification and publication.
- Add graph-only CLI execution and a graph quality artifact with source coverage, topic membership, rule/condition/exception counts, unresolved findings and provenance checks.
- Keep full-document authoring code outside this evaluation scope.

### D. Evaluation

- Build equivalent registration stories as prose, lists, tables and alternative heading layouts. Include repeated topics across stories, conjunction versus alternatives, negation, prerequisites and exceptions.
- Compare semantic graph meaning independently of source hashes, line numbers and surface Markdown; separately prove every variant's evidence resolves to its own original bytes.
- Exercise context boundaries, very long lines, fenced headings, skipped heading levels, table header context and ambiguous quotations.
- Test graph-only restart/resume, idempotent graph publication, rejected unsupported relations, incorrect topic merges, and absence of documentation-stage calls.
- Offline model doubles test contracts and routing, not real model quality. Report that distinction explicitly. If a live graph-only evaluation is performed, verify provider pricing/FX first, preserve the shared ledger and report observed quality without claiming universal invariance.

## Acceptance criteria

- All original substantive source fragments have exactly one extraction owner and traceable story context.
- Format-equivalent fixtures produce the same expected topics, rule meaning, logical groups, conditions and exceptions; source-specific evidence remains distinct and valid.
- Multiple stories about registration share a verified registration topic; unrelated scopes and contrary rules are not merged.
- No semantic edge is published without valid original-source support; quote positions select the exact stored text.
- Graph-only runs finish with a frozen graph and quality report, no plan or generated document, and can resume after a checkpoint without replaying completed stages.
- Missing/ambiguous context or semantic findings prevent a successful graph release.

## Delivery

Update this plan with implementation results and limitations. Deliver code, focused tests, graph-quality evidence and a refreshed inspector for a graph-only evaluation artifact. Do not claim a new full documentation pipeline validation.

## Implementation results

- Added `source_documents.py` with Markdown syntax mapping, exact original character locators, story ownership and supporting context. Oversized heading containers split at nested headings; large tables with unique record keys preserve per-record context, headers, surrounding qualifications and prior values for blank cells. Ambiguous oversized unstructured text fails explicitly.
- All 14 Markdown documents under `data` pass deterministic context construction: 5,131 source blocks, 923 structural stories/records and 506 owned batches. This checks parsing/context construction, not model extraction of the whole corpus.
- Added strict semantic contracts, typed relations, exact quotation tables, scoped topic reuse, complete fact allocation and precise quote-to-original-source retrieval. The inspector exposes the new nodes, relations and their exact citations.
- Added sequential proposal, independent semantic audit and publication nodes (steps 41–43), and `--graph-only` with no template dependency. The graph release gate checks semantic structure, provenance and source-aspect coverage.
- Added format-equivalent fixtures and graph-only checkpoint/restart tests. The focused offline checks pass 82 tests, including shared fixture compatibility. No documentation planning, writing or release test was executed.
- Tests found a pre-existing infinite-loop bug when extraction validation findings were appended while iterating that same list; fixed and covered by the owned-source rejection regression.
- Initial live evaluation found inaccurate model-counted quote offsets, overly narrow registration topics and response truncation. Added deterministic anchoring only for unique exact quotation text, retaining raw drafts and anchoring decisions. Strict validation still rejects ambiguous or altered quotations. Strengthened extraction/topic/audit prompts and reran with low thinking for extraction/proposal and medium for audits, with a 16,384 output-token limit.
- The second live evaluation exposed compound conditions retained as one node. Added exact `source_conditions` bindings to let a logical group decompose a verified compound phrase into elementary conditions without losing its provenance. The independent audit checks that decomposition's full meaning.
- The third live evaluation passes for all four formats: two topics, three necessary rules, three logical groups, seven elementary conditions and one exception. All 85 final quotation ranges resolve to the corresponding original fixture text. See [the evaluation report](2026-10-13-graph-evaluation.md) for observed results, prior failures, cost accounting and limits.
- Fixed source-coverage metadata to reference the frozen graph revision rather than its semantic content hash; regression tests verify the binding used by the inspector.

## Interpretation limits

- Formatting tests use a controlled semantic oracle to test parser, graph, ownership and provenance invariants. Real model quality is measured separately; neither test family establishes universal formatting invariance.
- Topic equivalence and semantic entailment remain model judgments checked by an independent audit. No fuzzy automatic topic merge is used.
- An exception targets its owning rule. A narrower affected prerequisite is preserved in the exception statement; this graph is not an executable policy engine.
- Exact source locators are ready for downstream retrieval. Full documentation generation and rendered citation navigation are outside this validation scope.
