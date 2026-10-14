# Document authoring quality and consistent presentation

## Accepted objective

Improve the reusable documentation pipeline after evidence and graph preparation. Preserve original meaning and provenance while producing a coherent, attractive business document. Keep the approved plan as the structural contract. Preserve historical outputs for comparison; never manually improve a generated result to disguise pipeline defects.

## Implementation

1. Represent section hierarchy explicitly in the plan and document. Show a readable outline, scope, source bindings and proposed visuals for user approval. Render heading levels and numbering deterministically. A subsection always retains its parent; structural parents need no invented filler. Source document formatting does not dictate graph semantics.
2. Replace HTML visual wrappers with Markdown images and Mermaid blocks followed immediately by consistent numbered, descriptive captions. Store visual kind, content/asset, caption and evidence separately. Validate links, caption presence and diagram syntax; preserve source traceability for visual claims.
3. Use high reasoning for planning, writing, editorial review, repairs and semantic verification without changing the configured Gemini provider/model. Add checkpointed editorial and revision-validation stages after factual drafting. Up to three targeted correction rounds, with early stopping and a 20-minute run budget. Reuse source preparation and the graph; do not restart them for prose defects.
4. Persist candidate versions and retain stable content identities. Reject structural loss, invalid citations and unsupported changes rather than automatically replacing a stronger previous version. Review summaries, diagrams, terminology and detailed rules for consistency. Audit explanations are feedback, never evidence. Report incomplete validation honestly and preserve existing manual plan/final review gates and unattended autopilot behavior.
5. Test hierarchy, captions, preserved facts, bounded corrections, rollback, source links, persistence and manual review. Compare the previous frozen output with fresh full runs, judging consistency, sourcing, information preservation, readability and visual quality. Separate deterministic checks, model estimates and independent semantic review. Use additional varied data and order-masked comparisons where feasible; do not claim blind evaluation on known development fixtures.

## Delegation

- Structure agent: plan/document hierarchy, Markdown renderer, structured visuals, template/prompt presentation contract and focused regression tests.
- Workflow agent: high-reasoning configuration, checkpointed editorial and revision-validation workflow, bounded corrections, preservation/rollback and focused tests.
- Evaluation agent: predeclared comparison criteria, diverse acceptance fixture, independent source and readability review; no editing generated documents.
- Coordinator: interface integration, remaining publication/preview support, full tests, measured live runs, visual inspection, consolidated report.

## Acceptance

No orphan subsection, numbered pseudo-heading in body text, HTML visual table, missing caption or broken local visual/evidence link. Approved planned content remains represented. Revisions must not silently delete supported information. Exactly matched quotes do not prove entailment; remaining semantic defects must be explicitly reported. Run the same brief/source corpus for before/after comparison where possible and disclose template, reasoning and workflow changes. Record requests, repairs, wall time, user/coordinator intervention and unresolved findings.
