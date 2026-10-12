# Implementation Plan: Readable Documentation from Markdown

Date: 2026-10-11

Status: proposed implementation plan. This file defines the next work in `new-approach`; it does not claim that the changes or acceptance tests are complete.

## Goal and boundaries

Improve the final Markdown documentation generated from user-supplied Markdown sources. Keep the existing immutable evidence, original-source citations, complete obligation accounting, approved page plan, LangGraph checkpoints, and final human release review. The output should follow the supplied template, explain each substantive rule in a clear primary location, use helpful tables and diagrams, and include relevant source images when supported.

This increment is document-only. Do not add code-source analysis, wait for the old pipeline's furniture run, build a website, or interpret image pixels with a model. Support local PNG, JPG/JPEG, and SVG source assets. Diagram generation means Mermaid code fences; diagrams are optional unless the approved template and available evidence require one.

The main performance rule is to improve the content contract and deterministic assembly inside existing paid stages. Do not add a model call for every claim, asset, diagram edge, or editorial repair. Keep the current `gemini-3.8-flash` policy and shared spending ledger.

## Observed starting point

- The approved furniture release covers 457 graph assertions and links all 240 user-story fragments, but its Markdown contains repeated descriptions across the executive summary and feature sections. The comparison report counts 17,261 whitespace-separated words in the file; this includes citation syntax and is not a rendered reading-length measure. The released title also contains `Documentation Plan`. These are quality issues, not evidence-coverage failures. See `../furniture-generation-comparison.md` and the frozen `furniture-new-v5` candidate.
- `compile_template` currently keeps the template text and required `##` headings. Its structural validator checks headings, but not required tables, callouts, diagram slots, conditional sections, or the purpose of each section.
- `draft_page_plan` assigns every assertion exactly once to a section. `write_section` asks for one mapping per obligation, which preserves accounting but encourages a separate prose treatment for semantically overlapping assertions. The editor is told not to change structure or add diagrams.
- `selected_files(..., "docs")` currently excludes every non-`.md` file, including the four referenced SVG mockups in `data/test_data_1/assets`. The current candidate export therefore contains no copied visual assets.
- The existing furniture run used 316 settled model calls for its successful v5 revision. A like-for-like timing baseline has not been established; do not claim a speed gain from the available call count alone.

## Content contract

Keep all accepted source assertions as auditable obligations. Add a presentation layer that groups obligations without deleting them:

| Record | Required meaning |
| --- | --- |
| `ContentUnit` | A reader-facing topic with one canonical section, all contributing obligation IDs, common facts, scoped variants, conditions, exceptions, and evidence IDs. Similar wording alone does not prove two facts are equivalent. |
| `PresentationPlacement` | The exact paragraph, list item, table row, image, or diagram element that represents one or more obligations. Many obligations may point to one placement when the placement faithfully expresses them all. |
| `TemplateRequirement` | A versioned requirement extracted from the frozen template: heading, ordering, section purpose, required table/callout/flow, conditional rule, or style instruction. Example facts remain layout examples only. |
| `SourceAsset` | A frozen binary asset with safe relative path, content hash, detected format, dimensions where applicable, source references, and disposition. |
| `VisualPlacement` | A planned image or diagram with section, reader purpose, source/evidence IDs, caption or text alternative, and review status. |
| `DiagramSpec` | Mermaid type and source, plus evidence mappings for material nodes, transitions, labels, branches, and exceptions. |

One content unit has one detailed home. An executive summary or related section may refer to its outcome briefly and link to that home. A repeated numeric value, status, or rule should appear again only when the reader needs it locally; the second occurrence must retain its scope and source. Role-specific differences belong in a compact comparison when the common behavior is shared. Distinct scopes, versions, conditions, or exceptions must remain visibly distinct even when their prose is similar.

Coverage remains exact at the obligation level. The validator must accept multiple obligations mapped to one supported placement, reject an obligation with no placement, and reject a placement that claims evidence for only some of the facts it states. The audit file retains the complete mapping; the reader page does not expose internal obligation IDs or graph terminology.

## Template fidelity and page structure

Extend `compile_template` to produce an explicit `TemplateRequirement` inventory from the frozen Markdown template. At minimum, retain required heading order, section purposes, table columns, callouts, requested primary flow, conditional sections, and document metadata. Validate the approved plan and final output against this inventory. Record an explicit inapplicability decision for a template element that the source cannot support; never fill a sample placeholder with invented product facts.

Extend the existing plan draft and review to show canonical content units, section ownership, brief overview placements, required visuals, asset candidates, and any template exceptions. The exact plan hash must include these fields. The existing `review_plan` interrupt remains the only approval path before writing; changed content ownership or visual choices require a new approval revision.

Prefer a reader-oriented layout within the approved headings: a short summary and navigation aid, capability overview, one detailed explanation per capability, compact variation/rule tables, a supported process flow, and a concise limitations section. Avoid a second full account of the same feature in the executive summary, roles section, and source-coverage section. The release title describes the product or system, never the planning artifact.

## Images and attachments

Extend document selection and snapshotting to inventory `.png`, `.jpg`, `.jpeg`, and `.svg` files under the selected document root. Resolve Markdown image references relative to their containing source file. Preserve referenced and unreferenced assets in the inventory with distinct dispositions; do not silently include an unrelated image in the reader document.

- Freeze selected asset bytes in the content-addressed store, with a source-relative path and hash. Repeated references to the same bytes share one stored object and one exported file.
- Validate extension against detected content. Enforce configured byte and pixel limits for raster images. Reject broken paths, links outside the selected root, symlinks, malformed files, and unsupported formats visibly.
- Parse SVG as inert data. Reject scripts, event handlers, active content, remote references, and unsafe XML constructs before copying it into the output. Preserve the original hash and record any safe-rendering transformation separately if one becomes necessary.
- Use source-provided alt text when meaningful. A caption or explanatory alt text must come from nearby Markdown or attributed reviewer input; a model must not infer visual facts from unexamined pixels. Missing meaningful text is a review item when an image is needed for understanding.
- Plan image placement by relevance to the adjacent content, not by the number of source references. The repeated furniture mockup should appear where it clarifies a capability or flow, rather than once per user-story row. Keep a source-asset index for images not placed in the reader page.
- Export chosen images under stable relative `assets/` paths, use portable Markdown image links, include bytes and hashes in the candidate manifest, and verify links after copying the complete export to another directory.

An image is supporting material, not proof of a behavior the accompanying text does not establish. Its source, caption, and placement are inspectable in the audit artifacts.

## Mermaid diagrams

Choose a diagram only when it answers a reader question more clearly than prose or a table. Supported first-release uses are a process with consequential branches, a state lifecycle with documented transitions, or a sequence of handoffs between named actors. Reuse the template's requested flow location when applicable. Do not turn a list of unrelated features into a flowchart.

The approved plan records the diagram's question, type, intended section, and source-backed steps. The writer may produce a bounded `DiagramSpec` inside the existing section response, or deterministic assembly may use already structured transition records. Do not add a separate model request by default. Permit at most one primary diagram for a section; additional diagrams need a specific reader purpose in the approved plan.

Validate Mermaid syntax, safe labels, node and edge count, exact section placement, and all material node/edge evidence mappings. A condition on an arrow needs evidence for the condition; a transition cannot be inferred merely because its endpoints exist. Compare diagram statements with nearby prose and tables, including exception paths and unknown transitions. Provide a short text description for readers who cannot view the diagram. If evidence is insufficient, omit the diagram and expose the template gap for review instead of inventing a path. A clean model audit alone cannot waive failed structural or source checks.

## Workflow changes and cost control

Use the existing sequential LangGraph nodes and stable `thread_id`. Keep large immutable artifacts outside graph state and add checkpointed references before proceeding:

| Existing stage | Planned change |
| --- | --- |
| `snapshot_inputs` / `inventory_sources` | Discover, validate, freeze, and account for referenced source assets alongside Markdown spans. |
| `compile_template` | Produce the explicit template requirement inventory. |
| `draft_page_plan` / `validate_page_plan` | Assign canonical content ownership, choose visual candidates, validate template coverage and duplicate-risk clusters. Include choices in the approved plan hash. |
| `retrieve_section_evidence` | Supply mandatory obligations plus only the nearby evidence needed for the current content unit and approved visual. Preserve all qualifiers. |
| `write_section` / `verify_section` | Write one coherent treatment for a content unit; allow one passage or table row to map several obligations. Generate only approved evidence-backed Mermaid specs. |
| `assemble_pages` / `edit_page` / `verify_edited_page` | Assemble visual placements and perform bounded local deduplication without changing canonical facts or template structure. Revalidate every changed factual placement. |
| `audit_documentation` / `export_candidate` | Check final obligation-to-placement coverage, template elements, repetition findings, diagram entailment, asset safety, portable links, and manifest hashes. |

Keep `interrupt()` and `Command(resume=...)` for unresolved factual, asset, template, or release decisions. Avoid new approval screens and repeated whole-document model audits. Reuse the existing section verification call for changed diagrams and prose, and rerun it only for affected sections after a repair. Reject oversized context rather than silently truncating mandatory evidence; split a content unit at a meaningful boundary if needed.

Track paid calls, input/output tokens, model-response time, wall time, retries, and verification repairs by stage. Compare like-for-like runs on the same selected Markdown fixture, template, model, limits, and cache mode. The implementation target is no extra routine model call per asset or diagram, no increase in paid call count for the representative fixture, and no more than 15% added end-to-end wall time. If a live timing comparison is unavailable, report that target as unverified.

## Implementation sequence

| Step | Deliverable | Exit evidence |
| --- | --- | --- |
| 1. Quality baseline | Freeze the current furniture candidate as a comparison artifact; annotate a small document-only set containing shared behavior, role variants, repeated values, conditions, exceptions, a real flow, and visual references. Define reader questions and a repetition rubric. | Every selected fact has source spans; current repetition, length excluding URL syntax, readability findings, and stage cost are recorded. No old-pipeline run is needed. |
| 2. Template and content ownership | Add template requirements, content units, canonical section ownership, and shared placement mappings to the plan and validators. Update plan review output. | The plan still allocates every obligation; duplicate facts have one detailed home; scoped differences and required template elements survive. |
| 3. Asset support | Add binary snapshot, safe validation, source-reference resolution, placement, export, and manifest checks for PNG/JPEG/SVG. | Referenced images render from a copied export; repeated references do not create repeated files or reader placements; unsafe and missing assets block or remain visibly unresolved. |
| 4. Reader writing and diagrams | Update the plan/writer/editor contracts and prompts for compact narrative, purposeful tables, and evidence-mapped Mermaid diagrams. Keep work in current paid stages. | Summary and detail no longer duplicate full descriptions; useful source-backed diagrams appear where planned; unsupported diagrams are absent. |
| 5. End-to-end verification | Extend deterministic audits, section source checks, portable export, release review, and regression fixtures. | No lost obligation, qualifier, citation, template requirement, or manifest entry; exact approved hashes still gate release and restart. |
| 6. Small document-only evaluation | Run one bounded revised fixture after offline checks and compare it with the frozen baseline. Expand to a larger document-only sample only if the first result passes. | Publish factual fidelity, repetition, reader rubric, visual usefulness, call count, time, and cost separately. |

## Tests and acceptance

Run deterministic tests first. Include fixtures for identical wording with different scopes, repeated role variants, a shared rule with a distinct exception, a value repeated across sections, summary/detail overlap, template examples that look like facts, required versus optional template elements, and a deliberately unsupported diagram. Exercise flow, state, and handoff diagrams with cited branches; reject an invented edge and a false guarantee. Test valid PNG, JPG/JPEG, and SVG files; duplicate references; broken and escaping paths; malformed or active SVG; oversized raster; absent alt text; and copied-export links. Restart before and after plan review, section verification, export, and release review without losing accepted work.

Acceptance on the annotated document-only sample requires:

1. Every annotated fact, condition, exception, scope, and uncertainty remains in the output with correct original-source support; zero unsupported material claims or Mermaid edges.
2. Every obligation has a final placement, every required template element is present or has a reviewed inapplicability decision, and the approved plan remains revision-bound.
3. No full paragraph is duplicated across sections. The count of reviewer-marked redundant explanations falls by at least 50% against the frozen candidate. Word count is diagnostic, not a reason to discard information.
4. A human reader scores at least 4/5 for structure, clarity, findability, and visual usefulness, and answers the preregistered questions with their material qualifications.
5. Included images and Mermaid diagrams are useful, source-traceable, readable as text, and portable in the exported bundle. Zero unsafe or unresolved visual references are published.
6. The representative like-for-like run meets the call and wall-time targets above. Publish any unmet or unmeasured target explicitly.

The current repository instructions specify a cumulative PLN 200 development API allowance, while the local shared ledger and configuration recorded during the furniture run disagree with that limit. Complete the offline work first. Do not make another paid Gemini request until the governing allowance is reconciled; keep every eventual request in the existing shared ledger.

## Completion definition

The increment is complete when a user can provide Markdown sources, an optional set of referenced PNG/JPEG/SVG images, and a Markdown template; approve a plan showing content ownership and visual choices; receive a concise, readable, evidence-backed document with relevant tables and Mermaid diagrams; move the exported bundle without breaking local visual links; inspect complete source and visual provenance; and resume any interrupted stage. Report measured quality and runtime separately from structural test passes.
