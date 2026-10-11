# Generation Plan: Synthetic Furniture Commerce Sources and Direct Source Citations

Date: 2026-10-11

Status: fixture and both citation exporters implemented. Automated matching and targeted tests pass; browser navigation remains to be checked in an environment that permits a local HTTP server.

## Outcome

Produce four substantial, synthetic business source documents for a furniture retailer that sells configurable furniture and provides a 3D kitchen planner. Use these sources to exercise both independent documentation pipelines. A citation in final generated documentation should open the original source page at the cited passage, using a Scroll to Text Fragment URL when the source has a usable web URL. Keep the immutable source snapshot and local source index for audit.

## Source package

| Document | Business scope | Approximate size | Source URL |
| --- | --- | ---: | --- |
| `data/test_data_1/shopping-and-discovery.md` | Catalog, selection, discovery, materials, and guidance | 82,000 characters | `http://127.0.0.1:8765/shopping-and-discovery.html` |
| `data/test_data_1/kitchen-3d-planning.md` | Room setup, 3D cabinet planning, design checks, and handoff | 78,000 characters | `http://127.0.0.1:8765/kitchen-3d-planning.html` |
| `data/test_data_1/checkout-and-fulfilment.md` | Basket, payment, delivery, installation, and after-sales | 77,000 characters | `http://127.0.0.1:8765/checkout-and-fulfilment.html` |
| `data/test_data_1/merchant-and-service-operations.md` | Assortment, approvals, pricing, review queues, and service work | 77,000 characters | `http://127.0.0.1:8765/merchant-and-service-operations.html` |

Each Markdown file has YAML-like front matter with `source_url`, `source_system`, `source_id`, and `source_revision`, then one title and one large Markdown table. Every row has an ID, an English `As a ... I want the system to ...` story, a preliminary product solution, an implementation solution, and an optional mockup with a behavior description. The implementation prose describes business ownership, handoffs, status, and acceptance rather than low-level software design. The corpus contains 240 distinct scenario rows across four documents. The synthetic content does not assert real customer or production facts.

`scripts/generate_test_data_1.py` regenerates the package deterministically. It also writes four HTML mirrors under `data/test_data_1_html/` and four SVG interface mockups under each package's `assets/` directory. The Markdown and HTML are generated from the same row records, so their visible story and solution wording stays aligned while their formatting differs. The SVG images are conceptual mockups, not screenshots of an implemented application. Serve the mirror with `python -m http.server 8765 --bind 127.0.0.1 --directory data/test_data_1_html` from the repository root. The `source_url` values intentionally point to that local server; a later Confluence or Jira import can set those values to real page URLs without changing the citation contract.

## Direct citation contract

1. Snapshot source bytes as before, including the metadata. Associate each evidence span or table row with its file's `source_url`; never ask the model to invent the URL.
2. Keep the evidence ID, original Markdown path, line range, snapshot hash, and exact excerpt in audit artifacts. The web URL is a navigation target, not a substitute for frozen provenance.
3. Derive a text directive from source wording that is expected to be visible in the rendered HTML. For a table row, prefer the unique user story in the same row; for prose, select a plain-text phrase from the evidence. Remove Markdown-only syntax, decode HTML entities, and collapse whitespace. Never use a raw table line containing pipes or image syntax as the query.
4. Encode a fragment as `#:~:text=<percent-encoded visible phrase>`, or append `:~:text=...` to an existing element fragment. Percent-encode reserved directive characters, including comma, ampersand, and hyphen. Keep the source page's path and query unchanged.
5. Use the direct source URL for the reader-facing citation in both approaches. Preserve the local `sources/index.md` or `source-index.md` and evidence files as an audit trail and fallback for sources without an approved web URL.
6. Validate source URLs as HTTP(S), limit direct links to URLs declared in the frozen source metadata, and check at least one representative link per HTML mirror in a browser. For authenticated Confluence/Jira pages, validate against an accessible rendered page when available; if the visible text differs in wording rather than formatting, regenerate the snippet from that page or use a stable page/element anchor. Do not claim that a text fragment can survive arbitrary content edits or that all browsers will highlight it.

The fragment target is the rendered page text, not the source Markdown. Browser matching tolerates many whitespace and element-boundary differences, but it still requires matching words in the destination. A local HTML mirror provides deterministic verification; remote systems may insert labels, hide content, change wording, or require login. An unsupported browser opens the source page without highlighting. These behaviors follow the [WICG text fragment syntax](https://github.com/WICG/scroll-to-text-fragment/blob/main/index.bs) and [MDN usage guidance](https://developer.mozilla.org/en-US/docs/Web/URI/Reference/Fragment/Text_fragments).

## Pipeline work

| Stage | Old approach | New approach | Completion evidence |
| --- | --- | --- | --- |
| Ingest | Read `source_url` from frozen Markdown source bytes and associate it with cited table rows. | Read `source_url` from frozen document snapshot and associate it with legacy evidence spans. | URL comes from the exact snapshot used for the citation. |
| Resolve | Convert the cited row's story or prose excerpt to a visible-text query. | Apply the same rule to `Legacy Dn`; retain local evidence for `Code Cn` unless code has a separately verified web URL. | No raw Markdown delimiters appear in the query. |
| Export | Render the direct link for `[S#]` in documentation and source index. | Render the direct link for `[Legacy D#]` in documentation and source index. | Click opens the declared source page at a matching passage. |
| Validate | Allow only exact declared HTTP(S) source page URLs in addition to existing local links and immutable assets. | Check generated links and evidence mapping before candidate review. | An arbitrary external URL is rejected. |
| Audit | Retain `sources/index.md`, snapshots, source labels, and source map. | Retain `source-index.md`, `evidence/D#.md`, snapshot hashes, and mapping audit. | Citation can be traced to frozen evidence after the web page changes. |

Use the existing persistent LangGraph checkpoints and stable `thread_id` in each pipeline. Citation resolution belongs to the existing sequential export stage, so it does not introduce a separate pause path. Human review remains through `interrupt()` and `Command(resume=...)`. The fixture generator is deterministic and makes no Gemini call. Live pipeline evaluation uses the shared ledger and `gemini-3.8-flash`; the user authorized raising the cumulative limit from PLN 200 for this evaluation. Its execution and costs are recorded in `furniture-generation-protocol.md`.

## Acceptance

- Exactly four Markdown source files, each approximately 80,000 characters, with valid source metadata and one large table.
- Every row contains a unique ID and an `As a ... I want the system to ...` story. Product and implementation descriptions are present and nonempty.
- The HTML mirror contains the same human-readable story and solution text; the mockup links resolve in both packages.
- A direct citation for a representative row in every document has a decoded `text=` phrase present in the target HTML page and lands on that row in a supporting browser.
- Both exporters keep their local evidence index and use direct source links where metadata is available; sources without metadata retain the existing local audit link.
- No live model calls are needed to generate or validate this fixture.

## Verification record

The generator produced four Markdown files of 77,205–82,370 characters and 60 story rows each. Automated checks confirmed that the text directive from every one of the 240 rows appears in its corresponding rendered HTML text, despite the Markdown table and HTML table using different markup. The new approach's source-link, evidence, and restart tests passed. The old approach's source-link and selected existing citation/Markdown validation tests passed. Ruff passed for the changed Python files. The local HTML server returned HTTP 200 outside the execution sandbox. Browser screenshots verified that text-fragment links highlight both an early and a late row of the HTML table and scroll to the latter. See the execution protocol for the commands and findings.
