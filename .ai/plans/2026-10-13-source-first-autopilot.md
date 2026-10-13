# Source-first knowledge and bounded autopilot

## Accepted design

Original sources remain authoritative. The graph is a navigational interpretation, not a mandatory executable logic model. Prefer a single substantial context over elaborate retrieval for small corpora. Use overlapping bounded source windows for larger corpora, without making headings, table rows or story identifiers semantic boundaries. Preserve immutable source locators.

Analyze available images with Gemini and record descriptions, visible text, uncertainty and model provenance. Produce an enriched Markdown derivative with generated image titles; never overwrite original evidence. Let semantic analysis determine useful image and cross-document relationships. Do not introduce domain-specific identifier rules.

Preserve natural-language relationship explanations and uncertainty with exact source support. The active source-first contract uses concepts and explained relationships; formal condition groups remain supported only by the legacy contract. Resolve references from supplied context without inventing missing documents or treating matching identifiers as proven identity.

Autopilot must produce a useful source-backed artifact within its deadline when usable input exists. Use bounded local repair, retain unresolved disagreements, and fall back to source-grounded output when semantic processing fails. Reserve time for finalization. Never label degraded output as fully audited. Manual review remains a LangGraph interrupt; autopilot does not ask for intervention.

## Implementation ownership

1. Input preparation: source windows, image analysis support, enriched Markdown, and tests.
2. Knowledge: flexible semantic relationships, source-first retrieval, uncertainty, and tests.
3. Workflow: integrate preparation stages, graceful completion, bounded finalization, and tests.
4. Integration and evaluation: independent fixtures, baseline comparison, checks, one measured live run, and report.

## Evaluation protocol

Preserve the prior risk-profiling graph and report as the historical baseline. Compare the same original input with the new result, separating semantic correctness, source traceability, coverage, and completion. Do not equate node count or audit acceptance with quality. Explicitly inspect previously identified metadata leakage and incorrectly conjoined independent outcomes.

Add domain-independent cases: unformatted prose, formatting variants, cross-document references, ambiguous identifiers, conflicting versions, image evidence, and oversized input. Controlled offline tests verify mechanics; they do not establish real-model accuracy. Report which cases use live model outputs.

After implementation and offline checks, announce and start one fresh end-to-end run with a 1200-second budget, unchanged source corpus, shared usage ledger and no coordinator changes during the run. Record wall time, model calls, internal retries, degradation, final artifact, and coordinator/user interventions. A fallback export alone is not proof of useful documentation; review its contents. If the attempt fails, report failure rather than disguising a restart as a single successful run.

## Acceptance

- Persistent sequential stage checkpoints and stable run identity remain intact.
- No business meaning is inferred solely from formatting or identifier shape.
- Generated image interpretations are distinguishable from authored text.
- Uncertain relationships do not erase original claims or block autopilot.
- Retrieval supplies source context within bounded requests without requiring perfect graph construction.
- Autopilot has an explicit, tested finalization path for recoverable failures and deadline pressure.
- Quality comparison states regressions, uncertainties, and limits of corpus generalization.

## Implementation and evaluation result

Implemented source windows, adjacent context, image interpretation and prepared Markdown, free semantic relationships, bounded persistent autopilot, exact citations, finalization reserve and honest audit/export identity. Code and tests remain English. Original sources and the shared usage ledger are preserved.

The initial measured full attempt completed in 180.49 seconds without execution-time intervention but failed independent quality review: two invalid graph relationships discarded the entire semantic batch and the document audit referred to pre-quarantine content. One corrective development round added per-record graph salvage, pre-audit citation quarantine, audited-content hashes and stronger source-grounding instructions.

A separate second full attempt completed in 198.20 seconds, with eight model requests, one automatic citation rewrite, no human gate and no coordinator intervention during execution. Both attempts remain recorded. This is not a first-attempt success claim. The second result is `complete_with_limitations`; its graph and documentation still contain identified semantic strengthening errors, and the exported document has no applicable coverage estimate after semantic quarantine.

All 359 tests passed across the final full suite and one short-path Windows rerun. Two independent live stage evaluations retain both earlier failures and the final schema results. All eight final-schema cases pass structural checks; one retains modality drift. Large-context behavior has offline coverage but no production-scale live benchmark.

See `evaluation/source-first-comparison-20261013.md`, `evaluation/source-first-independent-review-20261013.json`, and the two per-process metric reports for the full scope, measurements, counterexamples and limitations. Successful bounded completion is demonstrated; universal semantic correctness or a percentage of preserved original meaning is not.
