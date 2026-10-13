# Grounded business output and bounded content preservation

## Objective

Improve pipeline behavior across inputs, without editing historical generated documents. Produce readable business documentation with precise source citations. Never silently delete a supported topic because a generated paragraph or its citation failed validation. Keep model/audit diagnostics separate from customer-facing prose.

## Implementation

1. Give generated sections and paragraphs stable internal identities. Repair only affected paragraphs using original context and exact source quotations. Validate audit targets instead of interpreting arbitrary indices as document numbering. Keep bounded retries and persistent sequential LangGraph stages. If safe synthesis cannot be recovered, preserve relevant verified source text and report degradation separately; never retain an unsupported invented assertion merely to fill a section.
2. Publish business prose and compact source references. Store audit explanations, generated-image provenance, repair actions and uncertainty diagnostics in a separate verification artifact. Real unresolved business conditions remain clearly expressed in sourced prose. Do not publish 'Withheld paragraph', AI-production commentary or invented section references.
3. Bind documentation-plan sections to source evidence. Use graph relationships as bounded navigation suggestions alongside original-source search, never as authoritative evidence. Keep full context for small inputs and add original linked fragments for larger ones. Add a controlled source-only versus graph-assisted retrieval evaluation on varied cases, explicitly distinguishing synthetic acceptance fixtures from genuinely held-out data.
4. Test omission prevention, stable repair targets, audit hallucinations, repaired citation support, customer-facing rendering, context bounds and source plan coverage. Run a fresh measured pipeline validation on a varied multi-document fixture, retaining historical outputs and recording all interventions and quality limitations.

## Constraints

Use English code, prompts, tests and artifacts; no code comments/docstrings. Keep Gemini model and shared usage accounting unchanged. No domain-specific identifiers, schema inferred from formatting, unbounded audit loops or manual intervention in autopilot. Explanations produced by an auditor are review data, not source evidence.

## Implemented and validated

Stable paragraph identities, targeted bounded repairs, source-bound plans, exact excerpt links, separate verification artifacts and two manual review gates are implemented. Graph-assisted retrieval remains opt-in because controlled comparison included a regression. The final two fresh autopilot processes completed in 202.13 and 106.73 seconds without intervention. A full suite of 402 tests passed.

Independent semantic review still found unsupported guarantees and a necessary-to-sufficient condition shift that accepted model audits missed. Structural preservation and traceability improved; semantic correctness is not considered proven. See `evaluation/grounded-business-output-20261013.md` for all four development validation processes, remaining findings and evaluation limits. Historical outputs were not manually corrected.
