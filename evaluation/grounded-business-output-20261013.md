# Grounded business output: implementation and validation

## Scope

This change modifies the reusable pipeline. Historical generated documents were not edited. Paragraph preservation, source grounding and business readability are separate acceptance concerns; successful execution and exact quotation matching do not establish semantic fidelity.

The pipeline now assigns stable internal section and paragraph identities, validates audit targets and repairs only affected content. An invalid or invented audit reference cannot delete a paragraph. Supported planned sections are retained, and exhausted repairs fall back to relevant verified source text with an explicit degraded result when necessary. Repair explanations never become new source facts.

Customer documentation contains prose, illustrations and compact source footnotes. Exact excerpts, source locations, original context, image interpretation provenance, uncertainty and repair records are available in separate evidence and verification artifacts. Real business conflicts remain visible in the customer prose.

Manual source-first mode asks for review at the plan and final result. Autopilot uses bounded automatic recovery. Both use the existing persistent LangGraph checkpoints and review mechanisms. Document generation allows one targeted citation/plan repair and one semantic repair, with at most two semantic document audits; it does not restart extraction for a paragraph defect.

Plans identify relevant original sources. Graph-assisted retrieval is optional and disabled by default: six controlled synthetic retrieval cases showed three improvements, two unchanged outcomes and one regression when a misleading edge displaced relevant source text. This is a navigation experiment, not proof of improved generated documentation.

## Initial live validation

Two independent fresh autopilot processes ran against frozen code, without coordinator intervention, user decisions, restarts or manual output edits:

| Corpus | Process time | Model requests | Targeted semantic repair calls | Result |
| --- | ---: | ---: | ---: | --- |
| Existing risk profiling example with two images | 197.56 s | 9 | 1 | complete_with_limitations |
| New three-document equipment library fixture | 114.59 s | 5 | 0 | complete_with_limitations |

The previous risk baseline took 198.20 seconds and eight requests. This change primarily improves preservation and provenance, not raw runtime. The new risk brief explicitly requested readable business documentation, so this is not a strict single-variable quality experiment.

Independent reviews found that both runs retained planned sections, avoided phantom withheld-paragraph notices and removed appended AI/audit diagnostics. Exact citations resolved. The risk output restored the previously lost consent topic. However, both accepted model audits reported 0.98 coverage while missing substantive unsupported claims. No 98% accuracy or information-preservation claim is justified.

The library output overstated reservation availability, inferred non-configurability, moved an approval condition onto request eligibility, and cited an unrelated title for a corpus-absence statement. The risk output invented retry triggers, generalized a particular recoverable failure, added timing/execution guarantees and emitted two broken inline image references. These findings are retained in the independent-review JSON files.

## Follow-up within this implementation

The writer, planner and existing auditor were tightened around action/condition alignment, unspecified triggers, unsupported guarantees and source silence. Unsupported template sections are omitted instead of filled with invented implementation details. Detailed rules are assigned a primary section to reduce inconsistent repetition. These are general prompt constraints, not fixture-specific corrections or a new audit loop.

The renderer resolves approved source image references to exported assets and avoids repeated insertion of the same image in a section. The source overview budget includes serialized evidence identifiers. A full-suite failure also exposed a real Windows concurrent path-resolution race; the storage containment check now handles equivalent extended paths while preserving traversal protection.

## Final live validation

The final pipeline version completed both corpora with no user or coordinator intervention during execution. Each used a fresh process and thread, without restart or resume. Development validation consisted of two rounds on each corpus (four successful processes in total); the generic pipeline changes between rounds were developer work and must not be confused with zero intervention inside a running pipeline.

| Corpus | Final process time | Model requests | Automatic semantic repair calls | Status |
| --- | ---: | ---: | ---: | --- |
| Risk profiling and two images | 202.13 s | 9 | 1 | complete_with_limitations |
| Equipment library, three documents | 106.73 s | 5 | 0 | complete_with_limitations |

Risk retained 8/8 planned sections and all 16 initial paragraph identities. Its 63 citation uses matched exact evidence, 24 excerpt links resolved, and all three displayed image references resolved to two exported assets. The targeted repair corrected the invented retry triggers, generalized recovery claim and unsupported implementation prerequisites. However, the final accepted audit still missed execution guarantees such as avoiding re-evaluation, an unsupported reliability claim, and an image passage whose quoted excerpt was less specific than its description.

Library retained 7/7 planned sections and all 15 initial paragraph identities. All 39 citation uses and 30 excerpt files were verified, and all 17 declared topic checks were represented. The unsupported availability guarantee, non-configurability claim and empty UI template section disappeared. A remaining summary incorrectly stated that successful identity verification authorizes handover: the source establishes it as a requirement, not a sufficient authorization. The detailed section preserves the distinction, creating an internal inconsistency. The model audit accepted the document with a 1.0 estimate, so this result explicitly demonstrates that model coverage estimates cannot be used as an accuracy score.

There is a real improvement in preservation, usable sourcing, image links and separation of technical diagnostics. Semantic reliability remains insufficient for treating autopilot output as a verified client deliverable without review. The generated outputs have not been manually edited to hide these failures. Full independent findings are saved in `business-final-risk-independent-review.json` and `business-final-library-independent-review.json`.

## Automated checks and artifacts

The full regression suite passed: **402 tests in 134.68 seconds**. Ruff and JavaScript syntax checks passed. Tests exercise stable repair targets, invented audit references, omission handling, fallback behavior, business rendering, precise citations, manual review across restart, bounded source navigation and Windows concurrent filesystem behavior. These are behavioral checks, not a semantic accuracy certificate.

A subsequent read-only review identified a status edge case when repeated fallback repairs leave multiple source-extract paragraphs. The final status now tracks each surviving replacement paragraph independently. This status-only fix passed **29 targeted tests**, including two new integration regressions. The live runs did not use fallback, and were not rerun or modified. The validation manifest records the post-run change separately from the frozen live runtime.

The final inspection export is `.docgen/inspection-business-output/index.html` and reported zero export diagnostics. Process measurements and request accounting are in `business-*-pipeline-20261013.json`; the frozen runtime hashes and non-secret configuration are in `business-output-validation-manifest.json`. The two final runs charged approximately PLN 0.89 together to the existing shared ledger; all four validation runs charged approximately PLN 1.78, including the initial versions.

## Interpretation limits

Both live corpora are small and synthetic. The library criteria were written before its first live generation, but subsequent refinements were informed by observed failures, so final results are development validation rather than blind held-out evaluation. The graph retrieval experiment uses hand-constructed edges. Large heterogeneous production documents still need separate validation.

Preserving paragraph IDs and planned sections prevents structural deletion; it does not prove that every original fact was selected or paraphrased correctly. Exact source matches establish traceability, not entailment. Model audit judgments remain fallible. For inputs exceeding the bounded final audit context, the pipeline reports incomplete semantic validation instead of claiming a complete audit.
