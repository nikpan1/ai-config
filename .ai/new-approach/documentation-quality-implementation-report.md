# Documentation quality implementation and evaluation

Status: implementation and both fixture evaluations complete; candidates await human release review.

## Delivered behavior

`new-approach` now compiles a versioned template inventory covering heading order, purposes,
table columns, metadata fields, callouts, flow slots, conditional sections and style instructions.
Template sample rows remain examples. Unsupported requirements need explicit, revision-bound
inapplicability decisions in the existing plan review. Deterministic checks cover structural
requirements; the existing source audits check purposes, conditions and stylistic fidelity.

Content units keep canonical section ownership, every obligation, exact equivalent facts,
scoped variants, conditions, exceptions and evidence. Similar wording alone never merges facts.
Writers can map several obligations to one paragraph or table row. The final audit records exact
passages and character offsets into the exported page. Editorial changes require replacement
mappings for affected obligations; unchanged exact passages retain their existing mappings.
Changed passages are source-audited with nearby context and original evidence, and repetition
repairs revisit only affected sections. Editorial calls may change at most 12 obligation mappings;
unchanged factual passages remain verbatim. New unmapped claims are included in the change audit.

PNG, JPG/JPEG and SVG files are frozen and inventoried alongside Markdown. Local references are
resolved relative to their source file. Validation checks content versus extension, raster limits,
malformed files, symlinks, root escapes and SVG active/external content. Missing and rejected assets
stay visible and require explicit omission decisions when referenced. Alternative text must come
from source Markdown. No image pixels are interpreted by a model. Duplicate bytes share a stored
object and exported file; a source image gets at most one reader placement. The complete inventory
is retained even for unplaced images.

Approved process, lifecycle and handoff specifications generate a bounded Mermaid subset, with
individually mapped nodes and transitions, branch labels, text alternatives and source audits.
An independent audit must enumerate support for every material element. Structural or source
failures cannot be waived by an `accepted` flag. These changes use the existing paid planning,
writing and verification stages; there is no routine request per asset or diagram.

The existing sequential LangGraph stages, SQLite checkpointer, stable thread identifiers,
`interrupt()` reviews and `Command(resume=...)` remain in place. Exact plan hashes include ownership,
visuals and template decisions. Candidate manifests include image bytes and final audit records;
release checks validate manifests and portable local image links.

## Offline verification

- 79 Python tests pass, including source scopes and exceptions, shared placements, stale editorial
  mappings, rejected diagram edges, required versus optional template structure, source examples,
  PNG/JPEG/SVG validation, duplicate references, malformed and active SVG, byte/pixel limits,
  missing alternative text, symlinks, path escapes, copied exports and manifest tampering.
- XML safety checks run in the parser, including UTF-16 encodings, so processing instructions
  before or after the root and DTDs cannot evade a byte-level scan. Inert SVG encodings remain valid.
- Template validation uses the same section-heading normalization as export. Relative section
  headings are accepted at their exported levels, while genuinely missing headings still block.
- Full-size regression cases split shared topics by complete source-evidence size without dropping
  scoped variants, and keep large unchanged sections out of editorial source-audit requests.
- Grouped citations use one shared parser throughout writing, editing and export. Required named
  callout fields are retained. Root metadata is assembled once during export, and checks reject
  duplicate section metadata and copied template-writing instructions.
- Later writing units receive prior section headings and bounded complete passages for continuity;
  only the first unit receives section-level table and callout scaffolding. Bare citation labels
  are normalized in prose and mapped passages before source verification, while grouped citations
  and code examples remain intact.
- Antecedent context is added for leading references such as "Both roles" and explicit references
  to preceding rules. Self-contained user-story rows do not pull unrelated neighbors merely
  because they contain pronouns. All mandatory evidence remains intact.
- Blank-line-only editorial changes are excluded from factual change context. Changed claims,
  table cells and mappings still receive the normal bounded source audit.
- Restart tests inject failures at plan review, after section verification, before export and at
  release review. Accepted earlier work survives. Changed visual choices invalidate plan approval.
- Ruff and `git diff --check` pass. Wheel and source-distribution builds succeed.
- Generated flow, state and sequence syntax passed the actual Mermaid parser, in addition to
  deterministic subset checks. Parser dependencies were isolated under `.docgen/mermaid-check`.

## Annotated small fixture

The frozen pre-change run `quality-small-baseline-v1` and final run `quality-small-v6` use the same
Markdown, template, model, token limits and durable-cache mode. Both are fresh live runs. The final
implementation is frozen under `.docgen/quality-small-v6-src` for reproducibility. Earlier trials
and the export-only revisions remain recorded separately; they were not substituted for the final
result to improve its timing.

| Measure | Pre-change | Final revised run |
| --- | ---: | ---: |
| API calls | 26 | 20 |
| Input tokens | 54,523 | 68,030 |
| Output and reasoning tokens | 40,033 | 52,016 |
| Model response time | 344.57 s | 262.89 s |
| Invocation wall time | 345.64 s | 264.18 s |
| Ledger charge | PLN 0.74748 | PLN 0.96297 |
| Words excluding citation URLs and labels | 569 | 485 |
| Mapped extracted obligations | 13/13 | 16/16 |
| Source images included | 0 | 1 |
| Mermaid diagrams | 0 | 1 |
| Agent-marked redundant explanations | 9 | 0 |
| Reviewed template exceptions | Not represented | 0 required |

The final run made 23.1% fewer calls and its observed wall time was 23.6% lower. It overlapped the
furniture evaluation, so a controlled isolated timing claim remains unverified. The earlier
isolated pilot was 10.3% slower than the baseline; model latency and revision behavior vary. The
call target is met, and the 15% timing limit is met in this observation, without establishing a
repeatable speed improvement. Cost increased by 28.8% because token usage increased. The final
run needed one plan repair and no provider retry; no routine per-asset or per-diagram calls were
added.

The final document uses 14.8% fewer whole-page words and 16.9% fewer section words (557 to 463).
Counts are diagnostic and still include Mermaid source words. The counter preserves text between
links and excludes grouped citation labels. Different extracted obligation counts do not establish
fidelity; an agent reviewed all ten original annotated passages and answered all six preregistered
questions. Conditions, exceptions, currencies, regions, roles and unknowns survive. The correction
loop, specialist-only manual approval and fulfilment handoff have supported edges; no rejection
transition or delivery-time guarantee was invented.

Under the preregistered rubric, nine redundant full explanations of three scoped rules became
zero. Brief summary navigation and locally necessary process routing are excluded. The draft rule
and legal-hold exception appear together, while unknown deletion and history-retention periods,
rejection behavior and delivery guarantees are labelled in Limitations. Qualified answers therefore
require consulting that section. Diagram labels are smaller than body text at page width.
Independent human scores remain unmeasured.

Both manifests and all final placement offsets verify. A complete copied bundle renders its role
table, unchanged source image and six-node, seven-edge Mermaid diagram in the browser. Heading
navigation and text alternatives work. The candidate is at final release review, not a
human-approved release.

After the final parser and heading-validator fixes, `quality-small-safety-v1` revalidated all frozen
assets, renewed source-plan review and exported the exact same candidate hash and reader contents.
That development-only revalidation used one call, 14.45 seconds and PLN 0.06051; it is separate from
the fresh generation benchmark above and adds no routine asset-specific stage.
After the bounded editorial-diff fix, `quality-small-safety-v2` again renewed plan review and
exported the exact same candidate hash. It used one call, 13.03 seconds and PLN 0.04937.

Reproducible results are in `small-baseline-v1.json`, `small-v6.json`,
`small-final-comparison.json` and `small-reader-review-final.json` under the evaluation directory.

## Furniture comparison

The previous `furniture-new-v5` candidate
`e439237ddf6192a53bd9b99b8ba14edf760d91d33351d67cf875607483c3022f` was copied to
`new-approach/.docgen/quality-baselines/furniture-v5`; all files match its original manifest.
Its baseline has 15,591 section words excluding citation URLs/labels, 457 mapped assertions,
240 user-story links and 316 settled calls. A reliable like-for-like wall-time baseline is absent.

The full evaluation uses byte-identical Markdown and template inputs. It inventories four safe SVG
assets and 20 source references. `furniture-quality-v1` verified all 28 source batches and produced
512 obligations. Planning exposed oversized evidence groups, now split at scoped fact boundaries.
It also exposed the need to audit only editorial changes rather than a complete large section.
The accepted immutable graph is reused across explicitly recorded development revisions, with
fresh plan approval when the runtime changes. The current evaluation is `furniture-quality-v11`.
No earlier approval is carried forward. Revision v9 preserves 26 independently verified writing
units from v8 only after exact plan equality, a fresh source-plan audit and normal interrupt/Command
approval. It resumes the next unit after fixing an overly broad antecedent-context selection.
The revision provenance records the immutable accepted-writing reference and both runtime hashes.
Revision v9 completed all 72 writing units and three edited sections. Revision v10 retains that
accepted work after fresh plan review and asset revalidation, then checks the pending editorial
draft under the corrected heading validator. Revision v11 further narrows the factual diff so table
spacing does not force unchanged evidence into the editorial request. No failed editorial draft is
treated as accepted. The pending revision received fresh source-plan review and exact approval.
Intermediate planning exposed an output limit,
allocation-repair context, redundant audit instructions, grouped-citation checks and template
metadata leakage; these were corrected and covered by regression checks where applicable.
Early full-data writing also exposed repeated template framing in later chunks and unlinked
citation labels in overview tables. The current revision addresses both before source checking.
The full-data configuration now allows 65,536 output tokens, a conservative 600,000 request budget
and a 600-second request timeout. Interrupted and incomplete calls remain conservatively charged.
The source audit rejected invented transitions between independent feature stories. The final
plan records a reviewed inapplicability decision for the requested end-to-end flow because the
stories do not establish the transitions needed to draw it. Markdown and template hashes match
the baseline; the quality-focused brief differs, as recorded in `furniture-input-parity.json`.

The final `furniture-quality-v11` candidate
`506e4e1e39750197b099059b275df81f405a34147bd91e29e4e7447e5778dbee` reached release
review with 512/512 extracted obligations mapped to 407 exact reader placements, including 57
shared placements. The copied manifest and all final offsets verify. The revised document retains
all 240 source links from the baseline, includes all four safe source SVGs, and has no duplicate
paragraphs. It has 17,292 section words excluding citation syntax, versus 15,591 before: 10.91%
longer. The full-size fixture therefore does not demonstrate a word-count reduction, even though
the smaller fixture does. Its absent Mermaid flow is a reviewed source-evidence limitation.

The first full candidate passed the automated source audit, but a separate agent review of 24
preregistered source qualifications found one partial omission: its cabinet-placement passage
prohibited silent resizing but omitted customer acceptance for a suggested substitution. A
`request_changes` decision at the normal LangGraph release interrupt corrected the passage. The
revised section passed source verification and the whole document passed the final audit and
export checks. Agent review now confirms all 24/24 selected qualifications, equal to 24/24 in
the baseline; independent human acceptance remains unmeasured. This finding illustrates why
mapped obligation counts alone cannot establish complete source fidelity.

The final v11 revision recorded 20 paid calls and PLN 3.13815, including the correction. Those
numbers cover only that revision, which reused previously verified graph and writing, so they
cannot be compared as a fresh-generation efficiency result to the 316-call baseline. A reliable
like-for-like full-size wall-time baseline is absent. The complete selected development evaluation
ledger records 431 requests and PLN 77.78289 across revisions, including 11 conservatively
charged uncertain requests; the ledger was never reset. Results and evidence are saved in
`furniture-v11.json`, `furniture-final-comparison.json`, `furniture-reader-review.json`, and
`development-accounting.json` under the evaluation directory.

## Accounting and remaining acceptance evidence

Paid testing follows the user's autonomous-testing authorization for this task and retains the
existing shared ledger and configured PLN 1,000 guard. The ledger was not reset and the guard was
not disabled. This supersedes the earlier task-plan instruction to wait for allowance clarification.
Earlier failed schema experiments remain charged conservatively in the ledger and are separate
from the successful-run figures above.

The provider initially rejected the larger planning schema. The adapter now sends a simplified
schema and still validates responses with the complete local Pydantic contracts and deterministic
checks. A schema smoke test passed before the successful small run. Current model pricing was
checked against [Google's Gemini pricing](https://ai.google.dev/gemini-api/docs/pricing); the existing
dated exchange-rate record and conservative reservation policy remain in use.

Independent human scores of at least 4/5 for structure, clarity, findability and visual usefulness
remain unmeasured. No such acceptance is inferred from passing tests or model audits. The small
timing result is one observation, and a furniture speed claim requires a matching timed baseline.
The evaluation driver records its automated plan decision explicitly and preserves final human
release review. No old-pipeline furniture run was needed or awaited.
