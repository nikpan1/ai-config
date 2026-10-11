# Revitalization implementation and validation

Date: 2026-10-11

## Baseline and evaluation scope

Baseline measurements were recorded before changing runtime code in
`revitalization-baseline.json` and `revitalization-baseline-events.json`. The
historical small planning run used 79 paid requests, 578.49 seconds of wall time,
and PLN 2.96867. The historical small generation run used 72 paid requests,
906.98 seconds of wall time, PLN 8.00856, two completed review sessions,
three distinct review questions, and 152.59 measured seconds awaiting review.
The prior dense 500k-token deterministic fixture used 24,090 comparison tasks.
The shared development ledger initially held PLN 113.74228 charged and PLN
86.25772 remaining. These runs predate the new policy and are not paired live
speed measurements.

The retained dense fixture contains 2,619 claim records. The exact comparison
policy at a 48k reconciliation partition budget produced 6,206 model tasks,
3,428,271 required relationships, and the same 3,428,271 explicit pairs in the
durable queue. No required pair was omitted. This is 74.24% fewer tasks than
the historical 24,090, although each packed task still asks the model to check
its full explicit pair list. The largest estimated request was 67,657 input
tokens or 91,657 including the 24k reserved output, within the 100k request
setting. This is a local workload projection, not a completed live 500k run.
The measurement is in `revitalization-workload.json`.

A separate 500-record fixture with byte-equivalent records produced one
comparison representative, zero model tasks, and 124,750 pairs discharged by
exact equivalence. The original records and evidence remain in the bundle;
equivalence is used only to avoid redundant comparison calls. Results are in
`revitalization-duplicate-fixture.json`.

## Implemented behavior

- New runs default to versioned `exact` comparison and `consolidated` review;
  `strict` remains available for compatibility and diagnosis.
- Required relationships are assigned once across overlapping groups. Each
  task carries the exact required pairs and all applicable group contexts.
  Comparison responses must acknowledge exactly those pairs. Split tasks
  retain their pair and context coverage. The knowledge bundle records a
  comparison coverage manifest, representative membership, immutable plan
  references, and relationship membership; the planning importer validates it.
- Lossless request compression replaces an evidence excerpt only when it is
  byte-identical to the complete record statement or definition. Full source
  blocks still accompany the model request. Successful exact token-count
  preflights are cached by model and counted input.
- The consolidated review policy defers source inventory questions and
  evidence-backed reconciliation questions to a final knowledge dependency
  barrier. Invalid extraction, unsupported comparison references, and final
  coverage failures still stop at the affected stage. The Markdown report
  groups issues by type and gives each question its own evidence revision.
  CLI selectors submit revision-bound decisions through the existing LangGraph
  interrupt and resume path.
- Generated Markdown uses deterministic `[S1]` style labels, local citation
  links, grouped row citations, and a source index with exact passages and
  locations. A separate source map and accounting report retain exact evidence
  IDs and obligation dispositions. Validated generation and editorial reuse is
  the default and revalidates cached content before acceptance.
- Publishing a validated directory retries transient Windows permission
  failures. Reader-facing instructions and placeholder configuration were
  updated.

## Live and automated checks

The small synthetic ArchiveService source completed the knowledge phase with
Gemini `gemini-3.8-flash`: 11 paid requests, 67.89 seconds wall time, PLN
0.35195, zero review sessions, and zero unresolved issues. The run remained
within the shared PLN 200 ledger. This smoke result checks the new pair
contract and completed knowledge import on one small source; it does not
establish corpus-wide semantic quality. Its event breakdown is in
`revitalization-live-events.json`.

The first live planning run on that bundle completed without a human pause:
106 paid requests, 590.56 seconds wall time, and PLN 3.89121. It produced
23 writing jobs, 18 logical sections, and two pages. A semantic audit found
misallocated process topics and caused a bounded automatic replan. Its event
breakdown is in `revitalization-planning-live-events.json`.

The first live generation run reached `ready_for_review` without an
intermediate human pause: 51 paid requests, 450.92 seconds wall time, and PLN
5.20202. The release remains unapproved. Its event breakdown is in
`revitalization-generation-live-events.json`. Reading the candidate found
internal knowledge and source-selection identifiers in a metadata table,
although the model page review had passed. Fragment and editorial validators
now reject those identifiers in reader-visible text while allowing immutable
link destinations, and the prompts request a readable revision label and
source-inventory link. The later reader candidate confirms that visible
metadata uses R1 and the source inventory link. The exporter also groups
repeated canonical links by section.

A second planning run used a 40k writing-context setting on the same knowledge
bundle. It produced 21 writing jobs, 19 sections, and two pages, but took 143
paid requests, 1,232.24 seconds, and PLN 5.73242. Its semantic audit exhausted
two automatic repairs on a plan statement that incorrectly described archiving
as writing to “immutable storage.” A revision-bound component patch changed
that statement to “Archive eligible policy revisions”; all dependent stages
were rerun and the plan finished `ready_for_generation`. This was one
correction session, not a clean unattended planning run. Results are in
`revitalization-planning-40k-events.json`. The different model-generated
structure prevents treating the 23-to-21 job change as a controlled test of
context size alone.

The second generation run completed with 50 paid requests, 499.23 seconds, and
PLN 5.39678. It reached `ready_for_review` without an intermediate review
session, and its visible metadata uses a readable R1 label instead of artifact
hashes. Manual source review nevertheless found unsupported narrative claims,
invented table mechanisms, and diagram transitions connecting unrelated rules.
The broad page model audit had returned no blocking findings. A new targeted
audit now checks each reader-facing paragraph, table row, and Mermaid edge
against its local citations in sequential checkpointed jobs. A standalone live
probe of this candidate checked 80 units in ten paid batches (48.04 seconds,
PLN 0.19) and flagged 23 for
unsupported or insufficiently cited content, including the manually observed
retrieval and interface inventions. The probe is recorded in
`revitalization-claim-audit-probe.json` and
`revitalization-claim-audit-probe-events.json`; the full generation metrics are in
`revitalization-generation-40k-events.json`. This is a blocking quality finding,
not a claim that the second candidate is ready for release.

An isolated edge probe rejected the unsupported daily-run-to-tenant-check
transition when evaluated alone. Diagram edges are now batched separately from
prose in the targeted audit. The next planning revision used stronger edge and
table evidence instructions. It completed without a human pause in 563.50
seconds with 91 paid requests and PLN 3.71813, producing 20 writing jobs, 19
sections, and two pages. Its diagram specifications were inspected against
their linked source excerpts before generation. Planning events are in
`revitalization-planning-evidence-events.json`.

Generation from that plan stopped at the final writing job after 47 paid
requests, 474.60 seconds, and PLN 4.64. Its plan brief incorrectly required
the reader to see exact knowledge and selection artifact IDs in the Source
References and Coverage section. The writer used a readable R1 label, but its
fragment verifier followed the flawed brief and rejected the result. This is
a planning contract defect, not permission to publish raw IDs. The planning
brief validator now rejects the frozen knowledge revision and selection
reference in reader-oriented brief fields; prompts instruct the writer and
verifier to use the readable revision and source inventory. A new planning
revision is being tested. Events are in
`revitalization-generation-evidence-events.json`.

The fourth planning run corrected that brief contract. It completed with 87
paid requests, 641.54 seconds, PLN 3.63290, 20 writing jobs, 19 sections, and
two pages. It had no intermediate human review. The plan audit caught an
unsupported diagram edge and automatically rebriefed the section. The frozen
plan reference is recorded in `revitalization-planning-reader-events.json`.

The first generation attempt from that plan stopped at targeted factual audit:
107 claim units included 29 unsupported or unclear claims, including a diagram
relationship. `revitalization-generation-reader-events.json` records this
quality failure. Optional diagram removal and re-audit were then added to the
repair path, preserving complete source-backed prose when a diagram cannot be
supported.

The revised generation run reached `ready_for_review`. It used 148 paid
requests and 2,112.29 seconds wall time, costing PLN 9.56000. The final
independent audit classified 115 claim units as 111 supported and four
nonfactual, with zero unsupported or unclear units. Structural validation
accounted for all 23 in-scope obligations; the source map and 259 local
Markdown links resolved, and both exported file hashes matched the manifest.
The artifact is
`.docgen/runs/revitalization-generation-repair/documentation/0418c1321020c41e93c6095c889f1d6d3701b6f4926f52e12341a95b5ccc0992/index.md`.
Five intermediate correction sessions and 15 distinct issues were required:
three corrections to editorial coverage metadata and diagrams, followed by
two corrections to unsupported prose and source citations. The measured
completed review wait was 425.13 seconds. These technical and editorial
decisions were made during development; the final human release review has
not been performed. `revitalization-generation-repair-events.json` records
the full request and time breakdown.

The preregistered reader-question check found nine complete answers out of ten.
The remaining answer states that storage subsystems are unspecified but does
not explicitly say the scheduler technology is unspecified. The document is
also repetitive: the six substantive rules recur across overview, processes,
tables, and limitations, and some prose retains internal wording such as
“Claim ARCH-5.” This is a manual answer-location assessment, not the planned
blinded 4/5 human rubric. The detailed observations are in
`revitalization-reader-assessment.json`. A Mermaid renderer was not available,
so diagram syntax was inspected but rendering was not confirmed.

The local ingestion and batching scale check processed an estimated 2,695,006
source tokens across 35,001 blocks and 340 bounded batches in 2.59 seconds.
This establishes structural ingestion and batch ownership only; it does not
complete the 2m-token pipeline or establish its peak memory or artifact bound.

The final repository test suite passed: 133 tests in 594.43 seconds. Ruff
lint and formatting checks and `git diff --check` passed. Focused tests cover
exact representatives, pair and context coverage, task splitting, deferred
issues, revision-bound decisions, LangGraph resume, compact citations,
knowledge import, reader-visible identifier rejection, targeted claim audit,
and unsupported-diagram repair.

## Acceptance status and limits

| Plan target | Current evidence |
| --- | --- |
| At least 70% fewer dense comparison tasks | Met locally: 24,090 to 6,206 with all 3,428,271 required pairs queued. |
| Zero intermediate prompts on clean knowledge run | Met on the small live smoke source. |
| One grouped review for comparison conflicts | Covered by a graph test with two issues, final-barrier interrupt, and resume. |
| At least 80% fewer operator actions on a repairable fixture | Not established. The latest generation required five development correction sessions and 15 issue decisions. |
| Full source and obligation coverage | Existing validators and new comparison coverage checks pass on fixtures. A labeled semantic corpus assessment is still needed. |
| 40% fewer paid cold generation requests | Not met on the latest reader candidate: 148 paid requests, including 97 audit batches after repeated correction, versus 72 on a different historical source. A paired comparison remains unavailable. |
| 2x faster medium end-to-end run | Not measured or established. |
| Reader rubric of at least 4/5 and 90% reader answers | Nine of ten preregistered questions were fully answered in a manual check. The blinded rubric was not conducted, and substantial repetition remains. |
| Bounded concurrent requests and crash-race evidence | Not implemented in this increment. Execution remains sequential at durable acceptance boundaries. |
| Complete 2m-token local orchestration | Not established. A 2.695m-token structural ingestion check passed; the dense 500k comparison result is a task projection only. |
| Shared PLN 200 development ceiling | Enforced through the existing transactional budget ledger. Latest charged total: PLN 161.92162; reserved: PLN 0; remaining: PLN 38.07838. |

The reader-oriented structural plan redesign, page-level semantic partitioning
for very large editorial contexts, bounded concurrent prefetch, cross-revision
dirty dependency reuse, and acceptance-gated candidate pruning remain open
work. The latest candidate is evidence-backed but still repetitive and awaits
human release review. No claim of a finished M4 or M5 milestone is made from
the scale projections.
