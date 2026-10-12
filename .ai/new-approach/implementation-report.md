# New approach implementation report

Date: 2026-10-11

## Delivered

The independent `new-approach` package now has its own lockfile, environment example, CLI, tests, prompts, artifact store, SQLite graph, and SQLite LangGraph checkpointer. It reads repository-root `data/` inputs without importing or executing the old implementation.

The sequential LangGraph pipeline implements the named stages from input snapshot through final release. Each repeated code unit, document batch, graph batch, writing unit, and edited section has a checkpoint boundary. Plan, issue, and final-release reviews use `interrupt()` and `Command(resume=...)` on the same thread. Exact plan and candidate hashes gate approval. Invalid hashes return to the same review without drafting or publishing.

Selected source bytes are frozen as content-addressed objects. Markdown heading paths and code line spans resolve to those originals. Python AST inventories definitions, imports, and calls; unsupported selected text formats retain exact spans and declare generic-text capability. The graph stores typed assertions, source evidence, structural nodes and edges, FTS5 search, lexical seed matches, two-hop optional traversal, and unbounded mandatory qualifier closure. Published graph revisions include a SQLite copy and manifest. Cross-source assertion pairs with matching subject, predicate, and scope are review candidates rather than silently merged facts.

The writer uses mandatory approved allocations, original evidence, and read-only graph packets. Mechanical checks require a citation and exact supported evidence for each obligation mapping, followed by a separate Gemini audit. Edited sections are audited again. The candidate contains reader Markdown, a source index, cited evidence excerpts, audit metadata, and a file-hash manifest. The final approval validates those hashes before recording a release.

Model calls are fixed to `gemini-3.8-flash`, cached durably by prompt, payload, model, and implementation signature, and recorded against the existing shared ledger using its established `charges` schema. Missing or incompatible accounting data blocks a live call rather than creating a fresh budget. Source and template content remain data in the prompts.

## Verification performed

- Five deterministic tests passed, including restart across both human interrupts, stale plan-hash rejection, source-span integrity, secret exclusion, graph qualifier retrieval, portable candidate links, model allowlisting, and continuity of a synthetic historical ledger.
- Ruff passed on the new package and tests. A wheel build succeeded and included all ten versioned prompt files.
- An offline inventory using the shared `data/legacy-insurance` documents and `data/template.md`, with `new-approach/src` as a code fixture, selected 13 files and 957,590 bytes. It produced 1,734 source spans, 55 code units, and 166 document batches in 0.308 seconds. Python peak allocated memory was 8,444,419 bytes. These are inventory measurements only; they do not measure model quality or end-to-end throughput. See [offline-inventory.json](../../evaluation/offline-inventory.json).
- A live Gemini adapter smoke test returned a schema-valid code report after the contracts were adjusted to accept condition and exception arrays. A live dual-source fixture then reached the mandatory plan interrupt. The revised plan allocated all five extracted obligations once and gave all four template sections supporting source evidence. It recorded the disagreement between the code's age threshold of 18 and the legacy document's threshold of 21. Six paid calls in the final fixture run charged approximately PLN 0.071 through the shared ledger. Earlier repair and smoke calls charged approximately PLN 0.214 in the same ledger. The run stopped before any writing call or release approval.

## Open acceptance work

- No human-reviewed dual-source documentation release has been completed. The named code target was not supplied; the offline code fixture was this implementation's source tree, and the live plan used a small synthetic fixture. Semantic retention, citation entailment, and reader quality remain unmeasured on a reviewed source set. The live request cost is measured only for the small fixture.
- The Python AST adapter inventories call sites but does not resolve dynamic or cross-file calls. TypeScript, JavaScript, and other selected text formats are generic-text only. The current graph linker uses structural relationships and exact scoped subject links; model-assisted semantic candidate matching and measured lexical-mismatch recovery are not implemented.
- Oversized single source lines and oversized mandatory evidence closures stop visibly. Automatic partitioning of those cases, full conflict-saturation accounting, detailed table coordinates, and runtime/deployment interpretation need more work.
- The 100k, 500k, and 2m scale ladder, fault injection at every boundary, reviewed held-out semantic set, FTS-only ablation, and current live cost measurements remain open. The reported small offline inventory is not evidence for those targets.

The implemented vertical slice can run from selected inputs to two human reviews and a portable Markdown release. The quality and scale targets in the development plan remain acceptance targets until measured with actual source code and human review.
