# Document authoring comparison — 2026-10-13

## Scope and method

This evaluation concerns reusable documentation generation, not manual improvement of one document. Historical outputs remain unchanged. The pipeline now carries an explicit approved section hierarchy, renders numbering and visual captions centrally, and performs source-grounded editorial review with bounded candidate revisions and independent preservation checks. It exports Markdown and an HTML reading view with navigation and expandable exact source excerpts.

Two comparisons use the same sources and briefs as the earlier risk-profiling and equipment-library runs. The template, reasoning configuration and authoring workflow changed together; this experiment cannot attribute a result to any one change. A third, newly written repair-appointment fixture checks different operational rules and ambiguities. All three are synthetic, small acceptance corpora, not representative production samples. The reviewers know the development baselines; this is not a blind comparison. One output per final configuration is insufficient for statistical quality claims.

Criteria were recorded before the fresh runs in `document-authoring-criteria.json`. Exact quote matching, citation counts, stable paragraph IDs and the model's coverage estimate are not proof of claim entailment or measured information recall. Independent review checks conditions, actors, quantities, exceptions, modality and conflicting versions against original source text.

## Initial validation and corrections

The initial full runs are retained and are not counted as validation successes for the new planner:

| Initial run | Wall time | Result | Requests | In-run human/coordinator interventions |
|---|---:|---|---:|---:|
| Risk profiling | 498.98 s | Degraded source bundle; no completed authored document | 8 | 0 |
| Equipment library | 407.04 s | Document completed using fallback plan, with limitations | 9 | 0 |
| Repair appointments | 187.93 s | Document completed using fallback plan, with limitations | 7 | 0 |

All three hit a Gemini `400 INVALID_ARGUMENT` on the new planner response schema. Three isolated, ledger-recorded probes held the input, model and high reasoning constant: the schema with `maxItems: 40` failed, while `maxItems: 12` and the schema without `maxItems` succeeded. The correction preserves the application limit of 40 sections through local validation while omitting this constraint from the provider schema. It does not globally relax other structured contracts.

The initial risk writer exhausted its 32,768-token response budget twice. The first response contained 31,453 reasoning tokens and only 1,301 visible tokens, demonstrating why enabling high reasoning without output headroom is insufficient. Authoring now has its own 65,536-token output allowance and 420-second request timeout, both bounded by the overall run deadline. General graph-generation settings are separate.

Independent review of the initial library output also found a diagram that turned a necessary approval condition into a sufficient guarantee, despite correctly qualified prose and a positive model audit. Writer and editorial instructions now explicitly interpret each diagram path as an if-then claim. This remains a semantic judgment, not a deterministic guarantee.

These were developer interventions between validation batches. There were no manual content edits, checkpoint rescues, or human responses inside the initial runs. Costs and uncertain outcomes remain in the shared ledger; reserved uncertain amounts are not represented as known provider charges.

A subsequent batch named `authoring-final-*` was mistakenly launched inside the network-restricted sandbox. DNS resolution was denied, every model request failed before reaching the provider, and all three processes finalized degraded source bundles. These are environment failures, not valid quality samples. The unchanged implementation was then launched with approved network access under `authoring-verified-*`. Full process records for both preceding batches are retained in `document-authoring-initial-attempts.json`. A full test invocation also encountered temporary-directory permission errors in that restricted environment; the final test run uses the same short Windows temporary-directory setup as earlier successful runs with the required filesystem access.

## Visual evaluation boundary

The browser tool refused the local `file://` preview under its security policy. No alternate browser route or HTTP-serving workaround was used. Automated checks can verify heading hierarchy, captions, link targets, HTML structure and actual Mermaid grammar, but cannot establish pixel-perfect rendering, responsive appearance or subjective attractiveness. The exported HTML provides a reviewable reader view; browser-level visual acceptance remains unverified in this environment. Mermaid diagrams require access to the pinned CDN module; on failure the source definition remains visible with an explanatory notice.

## Implementation validation

The final complete test suite passed: **426 tests in 144.43 seconds**, after the schema and authoring-budget corrections. Ruff passed for runtime, tests and the presentation-inspection script. Tests cover explicit parent preservation and numbering, exact source links and structured visuals, targeted revisions, rejection of destructive or unsupported candidates, bounded rounds, high-reasoning request budgets, persistent restart behavior, and the manual plan/final review gates. These tests verify mechanics; they do not substitute for reviewing live generated content.

## Three-corpus live comparison before the final correction

All three `authoring-verified-*` runs used the corrected planner and full authoring budget. Every planner and writer succeeded. The provider then returned `503 UNAVAILABLE`, explicitly reporting high demand, during final audit work. The pipeline exported the retained drafts without waiting for a human. That validates unattended completion, but not successful semantic verification or editorial improvement. Risk and appointments have no completed semantic audit. Library's available audit applies to an earlier version and does not match its exported content. None completed the new editorial cycle.

| Case | Earlier baseline | New full process | Requests / successful responses | Editorial revisions | In-run interventions |
|---|---:|---:|---:|---:|---:|
| Risk profiling | 202.13 s | 472.23 s | 12 / 6 | 0 | 0 |
| Equipment library | 106.73 s | 505.48 s | 14 / 5 | 0 | 0 |
| Repair appointments | No previous baseline | 441.66 s | 10 / 4 | 0 | 0 |

| Mechanical measure | Risk before → after | Library before → after |
|---|---:|---:|
| Orphan numbered headings | 4 → 0 | 3 → 0 |
| Numbered pseudo-headings in body | 5 → 0 | 0 → 0 |
| Missing immediate standard visual captions | 4 → 0 | 0 → 0 |
| Citation uses | 63 → 141 | 39 → 79 |
| Distinct quoted-reference definitions | 24 → 52 | 30 → 35 |
| Body words under the same inspection method | 1,354 → 2,094 | 1,019 → 2,063 |

The plans' 14/15/15 sections, titles and parent links were preserved, as were all original draft paragraph IDs; library gained one paragraph. All local links resolved and every one of the four Mermaid definitions passed the real Mermaid grammar parser. There were no HTML visual tables. Appointments nevertheless had two captions with duplicated `Figure` prefixes, and risk placed two image assets five times. Counts alone therefore overstate presentation quality.

Independent semantic review found **mixed or negative content results**, despite the structural improvement:

- **Risk:** all eleven source rule topics remain represented, but repeated passages introduce unsupported acceptance guarantees, internal bypass assumptions, invented retry scope and Q3 exclusivity. More precise excerpts support some image values. Repetition and grammatical defects make parts of the longer document harder to read.
- **Library:** all seventeen reviewed topics are represented. The previous explicit identity-check-success-to-handover claim disappears, but new passages overstate name matching and extension rejection, and narrow the prohibition on silently substituting a different extension. The initial live audit correctly challenged a claim that turned staff permissions into responsibilities; the provider outage prevented verification of the subsequent fallback repair.
- **Appointments:** all thirteen selected topics appear; eleven checks passed and two contain inconsistent elaboration. The text/diagram invent broader pre-dispatch review and eligibility implications, and a dictionary entry invents contact-number verification. This is not a measured preservation percentage.

Sources: `document-authoring-independent-review.json`, `document-authoring-final-appointments-review.json`, `document-authoring-structure-review.json`, `document-authoring-mermaid-validation.json`, and `document-authoring-verified-runs.json`. No generated output was manually edited.

## Post-outage corrections and full authoring run

The renderer now removes model-supplied figure numbers before applying its own numbering; 16 focused structure/output tests passed. Transient 503 retries now wait 10 and 30 seconds, retaining the existing attempt cap and absolute run deadline; six model tests passed, including exhaustion of a short remaining deadline. General writing guidance now gives each detailed rule one primary location and discourages unnecessary restatements and repeated images. These changes address observed mechanisms without adding facts or rules specific to a fixture. Earlier failures informed these changes, so the last risk run is a development regression check, not held-out validation.

A real, ledger-recorded readiness call succeeded before starting one fresh `authoring-release-risk-20261013` run. The implementation and inputs were frozen again. The historical three-corpus outputs remain available for comparison.

That run completed in **762.10 seconds (12 minutes 42 seconds)** with 12 successful requests, no provider errors and no user/coordinator interventions inside the process. The settled ledger total was 2.5213 PLN. It performed two factual audits, one automatic repair covering six paragraphs, one editorial revision and independent candidate verification. The editorial revision corrected a diagram that had treated completeness as an acceptance guarantee. All 14 planned sections and 34 initial paragraph IDs survived. Body length fell to 1,674 words from the preceding 2,094; the longest prose block fell from 153 to 64 words. Four placements of two images still create repetition. Caption numbering, source links and actual Mermaid grammar checks passed.

However, this run revealed a reusable workflow defect: the second audit rejected seven text claims, but the independent editorial review was not given those outstanding findings and requested only a diagram change. The candidate verifier then accepted the diagram-only revision and supplied a clean whole-document audit even though the rejected text was unchanged. A final `accepted: true` flag therefore did not establish factual correctness. The untouched issues included regulatory characterization of consent, generalized discrete numeric constraints, scope claims backed only by an introductory sentence, and verification-gap commentary. The independent review also found an unsupported claim about avoiding repeat scoring.

This is why the subsequent implementation correction carries validated outstanding audit findings into editorial work and prevents an unchanged factual target from silently being certified as resolved. Only findings tied to the current document hash and real source/document targets are eligible; audit explanations remain diagnostic feedback, not source evidence. The run above is retained as a regression example rather than relabelled as a clean quality success.
