import argparse
import hashlib
import json
import sys
from html import escape
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from records.content import DICTIONARIES, QUICK_FACTS, REVISION, SERVICES, STORIES
from records.oracle import FULL_EXPECTATIONS, QUICK_EXPECTATIONS


ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data"
FULL = DATA / "test_data_2"
FULL_HTML = DATA / "test_data_2_html"
QUICK = DATA / "test_data_2_quick"
QUICK_HTML = DATA / "test_data_2_quick_html"
REFERENCE = DATA / "test_data_2_reference"
FONT_PATH = Path("C:/Windows/Fonts/arial.ttf")
SCREENS = {
    "dictionary-admin": ("Dictionary administration", "Q3 effective 2026-09-01", "Experience", "Horizon", "Loss tolerance", "Liquidity need", "Historical Q2 remains readable"),
    "integration-status": ("Integration status", "Local deterministic stubs", "RiskSignal: healthy", "MarketPulse: healthy", "CustodyBridge: healthy", "Last correlation: corr-042", "Severity S2 is operational"),
    "questionnaire": ("Risk questionnaire", "Q3 · draft D-104", "Experience: Beginner", "Horizon: 3–7 years", "Loss tolerance: 5%", "Liquidity: Flexible", "Processing consent CP-3"),
    "answer-validation": ("Answer validation", "Complete the highlighted answer", "Loss tolerance: 5.1%", "Invalid percentage", "Choose L5 or L10", "No provider request sent", "Draft remains editable"),
    "assessment-result": ("Assessment result", "Accepted profile P-204", "Band R2 · Measured", "Rules RS-2026-09", "Reasons: HORIZON_3, LOSS_5", "Accepted 2026-10-01 UTC", "Review after 365 days"),
    "profile-history": ("Profile history", "Prior results remain readable", "P-204 · R2 · Active", "P-151 · R1 · Superseded", "Q3 / Q2 provenance", "Failed attempts separate", "Open assessment details"),
}


def digest(content):
    return hashlib.sha256(content).hexdigest()


def bytes_at(path):
    return path.read_bytes()


def write(path, content):
    path.parent.mkdir(parents=True, exist_ok=True)
    encoded = content.encode("utf-8") if isinstance(content, str) else content
    if path.exists() and bytes_at(path) == encoded:
        return
    path.write_bytes(encoded)


def prepare_roots():
    allowed = {
        FULL: {".gitattributes", "01-dictionaries.md", "02-external-services.md", "03-risk-profiling.md"} | {f"assets/{name}.jpg" for name in SCREENS},
        QUICK: {".gitattributes", "risk-profiling.md", "assets/questionnaire.jpg", "assets/assessment-result.jpg"},
        FULL_HTML: {".gitattributes", "index.html", "01-dictionaries.html", "02-external-services.html", "03-risk-profiling.html"} | {f"attachments/8421/{name}-screen.jpg" for name in SCREENS},
        QUICK_HTML: {".gitattributes", "index.html", "risk-profiling.html", "attachments/8421/questionnaire-screen.jpg", "attachments/8421/assessment-result-screen.jpg"},
        REFERENCE: {".gitattributes", "README.md", "manifest.json", "citation-cases.jsonl", "expected-facts.jsonl", "discrepancies.jsonl", "ticket-map.json", "source-page-map-full.json", "source-page-map-quick.json", "scopes/risk-profiling.json", "scopes/unrelated-trading.json"},
    }
    manifest_path = REFERENCE / "manifest.json"
    previous_hashes = json.loads(manifest_path.read_text(encoding="utf-8")).get("file_sha256", {}) if manifest_path.exists() else {}
    for folder, names in allowed.items():
        if not folder.exists():
            continue
        for item in folder.rglob("*"):
            if not item.is_file():
                continue
            relative = item.relative_to(folder).as_posix()
            if relative not in names:
                raise RuntimeError(f"Unknown fixture output: {item}")
            recorded = previous_hashes.get(item.relative_to(ROOT).as_posix())
            if recorded and item != REFERENCE / "README.md" and digest(item.read_bytes()) != recorded:
                raise RuntimeError(f"Fixture output was edited outside the builder: {item}")


def text(value):
    return escape(value, quote=False)


def md_cell(value):
    return value.replace("|", "\\|").replace("\n", " ")


def frame(title, source_id, url, rows, headers, intro, visuals, notes=()):
    metadata = ["---", f"source_url: {url}", "source_system: local-html", f"source_id: {source_id}", f"source_revision: {REVISION}", "---", ""]
    markdown = metadata + [f"# {title}", "", intro, "", "| " + " | ".join(headers) + " |", "| " + " | ".join(["---"] * len(headers)) + " |"]
    html_rows = []
    for row in rows:
        identifier, cells = row
        markdown.append("| " + " | ".join(md_cell(cell) for cell in cells) + " |")
        html_rows.append(f'<tr id="{escape(identifier)}">' + "".join(f"<td>{text(cell)}</td>" for cell in cells) + "</tr>")
    markdown += ["", "## Visual references", ""]
    figures = []
    for index, (screen, caption) in enumerate(visuals):
        if index == 0:
            markdown.append(f"![{screen} screen](assets/{screen}.jpg)")
        elif index == 1:
            markdown.append(f"[![{screen} view](assets/{screen}.jpg)](#visual-references)")
            markdown.append(f"![{screen} reference][{screen}-image]")
            markdown.append(f"[{screen}-image]: assets/{screen}.jpg")
        else:
            markdown.append(f'<img src="assets/{screen}.jpg" alt="{screen} screen">')
        markdown.append(f"Caption: {caption}")
        markdown.append("")
        figures.append(f'<figure id="figure-{screen}"><img src="attachments/8421/{screen}-screen.jpg" alt="{screen} screen"><figcaption>Caption: {text(caption)}</figcaption></figure>')
    if source_id.endswith("dictionaries"):
        markdown += ["The image-only block below is navigation artwork and does not assert a business rule.", "", "![decorative navigation](assets/dictionary-admin.jpg)", ""]
    if notes:
        markdown += ["## Operational cases and boundaries", ""]
        for identifier, heading, prose in notes:
            markdown += [f"### {identifier}: {heading}", "", prose, ""]
    html = (
        '<!doctype html><html lang="en"><head><meta charset="utf-8">'
        f'<meta name="source-id" content="{escape(source_id)}"><meta name="source-revision" content="{REVISION}">'
        f'<title>{text(title)}</title><style>body{{font:16px/1.55 Arial,sans-serif;margin:0;background:#f4f7f6;color:#183331}}'
        'main{max-width:1420px;margin:auto;padding:28px}table{border-collapse:collapse;background:white}td,th{border:1px solid #c9d5d1;padding:12px;vertical-align:top;min-width:150px}'
        'th{background:#d9e8e3;position:sticky;top:0}figure{display:inline-block;width:45%;vertical-align:top;margin:20px 2%}img{max-width:100%}'
        'figcaption{font-weight:600}tr:target{outline:3px solid #32745f}::target-text{background:#ffe28a}</style></head><body><main>'
        f'<h1>{text(title)}</h1><p>{text(intro)}</p><table><thead><tr>' + "".join(f"<th>{text(header)}</th>" for header in headers) + "</tr></thead><tbody>" + "".join(html_rows) + "</tbody></table><h2>Visual references</h2>" + "".join(figures) + ('<img src="attachments/8421/dictionary-admin-screen.jpg" alt="decorative navigation">' if source_id.endswith("dictionaries") else "") + ("<h2>Operational cases and boundaries</h2>" if notes else "") + "".join(f'<section id="{text(identifier)}"><h3>{text(identifier)}: {text(heading)}</h3><p>{text(prose)}</p></section>' for identifier, heading, prose in notes) + "</main></body></html>\n"
    )
    return "\n".join(markdown).rstrip() + "\n", html


def dictionary_notes():
    notes = []
    for group, title, owner, ticket, *rest in DICTIONARIES:
        definitions = rest[:4]
        exception, consumer = rest[4:]
        first = definitions[0].split("|")
        last = definitions[-1].split("|")
        prose = f"{title} is owned by {owner} in D-2026-09. The current entry {first[0]} means {first[2].lower()} The contrasting entry {last[0]} means {last[2].lower()} A writer records the code and revision together so a later label change cannot rewrite a historical assessment. {exception} {consumer} The transition set in the table applies only to this dictionary; it never authorizes a transition in another dictionary with a similar label. {ticket} owns the relevant behavior, while Q1 and Q2 history remains inspectable under its original effective definition. A value outside the listed set is rejected before an accepted profile changes."
        notes.append((f"rule-{group}", title, prose))
    return notes


def service_notes():
    cases = [
        ("RiskSignal", "Accepted proposal", "The backend sends Q3 answers, CP-3 consent, RS-2026-09 and one idempotency key to POST /assessments. A complete response contains a provider assessment ID, proposed band R1–R4, nonempty reason codes, matching rules version and evaluation timestamp. The platform validates every field, writes answer and provider audit documents in MongoDB, then accepts the PostgreSQL profile summary. The proposed band is not displayed as an accepted result before both writes needed for acceptance finish."),
        ("RiskSignal", "Duplicate submission", "The same draft and answer body with the same idempotency key returns the previously accepted result. A second key can be used only for a new submission attempt after the workflow permits it. Reusing the key for a changed body is a conflict. The local stub records calls so a test can check whether a retry reused the original key and whether duplicate application submission avoided a second provider request."),
        ("RiskSignal", "Unavailable provider", "A connection error or 503 can be retried once with the same request and key. A 422 validation rejection is not retried. After the retry is exhausted, the draft remains recoverable and a previous unexpired accepted profile remains current. A timeout can leave the provider outcome unknown; the fixture never maps that uncertainty to a low band or to a successful assessment."),
        ("RiskSignal", "Incomplete response", "An HTTP 200 response lacking a provider ID, reason code, timestamp, known band or matching rules version is incomplete. The platform records a failed audit when possible and does not insert an accepted profile. The support team can use correlationId to compare the local attempt with the stub call log. A manual provider proposal cannot be pasted into a result without a versioned acceptance record."),
        ("RiskSignal", "Cross-store failure", "MongoDB retains answer and request/response snapshots while PostgreSQL owns accepted profile status. Failure to store the Mongo evidence blocks acceptance. If the Mongo write succeeds and the later PostgreSQL transaction fails, an orphan audit may remain. Automatic repair of that orphan is planned under TICKET-2020; current customer history excludes it. This is not a distributed transaction."),
        ("MarketPulse", "Quote retrieval", "QuoteService retrieves a synthetic instrument quote by instrumentId and displays bid, ask, quote currency and asOf together. An ask below bid or a negative value is invalid. A stale asOf is labelled stale; a cached price is never called live without a fresh provider timestamp. The instrumentRisk field characterizes the instrument reference, never the investor's accepted risk band."),
        ("MarketPulse", "Trading session", "The browse view receives OPEN, CLOSED or HALTED market-session status. CLOSED permits historical quote display but not order placement; HALTED explains why a previously visible instrument cannot be traded. The session times are in UTC and must form a valid window. None of these market states changes a Q3 answer, a RiskSignal request or a prior profile summary."),
        ("MarketPulse", "Reference correction", "When category or lotSize changes in the provider's instrument reference, the order view refreshes its own validation. A missing lotSize prevents order quantity confirmation. Saved watchlist references remain readable when an instrument becomes unavailable. The correction belongs to the market-data team and does not cause an investor reassessment by itself."),
        ("MarketPulse", "Quote outage", "The quote view may retry one transient 503 read, then reports the quote as unavailable. It never reuses a stale price as if it were a new fill quote. The local stub exposes a separate call counter. During a risk-profile-only scenario that counter must remain zero, including when RiskSignal retries after a timeout."),
        ("MarketPulse", "Currency separation", "A quote currency labels the quoted instrument amount. It is not the account settlement currency and not an investor answer. If the order currency differs from cash balance currency, this reference slice requires an explicit separate conversion decision instead of assuming parity. A profile assessment neither requests an exchange rate nor infers risk from the displayed currency."),
        ("CustodyBridge", "Cash reservation", "OrderService sends accountRef, orderRef, amount, currency, reservationKey and correlationId to POST /reservations. A successful response includes reservationId and RESERVED status. The order may advance from NEW only after that custody response. Risk profiling does not reserve cash, create an order or call this endpoint during a profile submission."),
        ("CustodyBridge", "Insufficient funds", "A 409 insufficient-funds business response is not an infrastructure outage and is not retried as one. The order remains NEW or becomes REJECTED according to order policy; it never acquires a fake custody reservation. The current risk profile remains unaffected because assessment and cash reservation are separate platform workflows."),
        ("CustodyBridge", "Unknown reservation outcome", "After a three-second timeout, the platform cannot assume whether CustodyBridge created a reservation. A same-key lookup before repeated mutation is planned and is not implemented in this fixture slice. The current adapter surfaces the timeout without marking the order RESERVED. Reusing the same key with a different amount would be a conflict. Local tests should inspect both the order record and stub calls before claiming a single reservation."),
        ("CustodyBridge", "Settlement event", "A custody settlement event carries settlementId and settledAt. Duplicate delivery of the same settlementId must not create a second transition. A PLACED order becomes SETTLED only when the referenced reservation and order match. A settlement timestamp does not update a risk-assessment effective time or provider rules version."),
        ("CustodyBridge", "Blocked custody", "A BLOCKED custodyStatus prevents a new reservation even when the quote view still displays a valid instrument and the investor has an active profile. The UI should identify custody as the blocking owner. RiskSignal is not queried to repair a cash or custody problem, and a risk-profile retry should leave the custody stub call count at zero."),
        ("RiskSignal", "Request example", "For the seeded investor INV-100 the current request carries questionnaireVersion Q3, rulesVersion RS-2026-09, experience BEGINNER, horizon H3, lossTolerance L5, liquidityNeed FLEXIBLE, consentRevision CP-3 and a single idempotencyKey. The transport also carries a correlationId. The provider does not receive a marketing-consent flag, customer name, trading account balance or an instrument-risk label. The request is rejected locally if any required Q3 answer is absent, so an incomplete draft cannot be made complete by provider defaults. A support reader can compare the request fields with the versioned dictionary page without inferring a label from an opaque code."),
        ("RiskSignal", "Response example", "The deterministic stub can return proposedBand R2, reasonCodes HORIZON_3 and LOSS_5, responseRulesVersion RS-2026-09, evaluatedAt 2026-10-01T12:00:00Z and an opaque providerAssessmentId. Those fields describe a proposal. The platform records its own assessmentId after successful evidence and summary writes. The UI shows the accepted assessment ID and provider provenance together. If a valid HTTP response instead says responseRulesVersion RS-2026-01, the platform rejects it even if the proposedBand happens to be R2; a matching label does not repair a mismatched rule version."),
        ("RiskSignal", "Historical timeout definition", "Revision RS-2026-01 treated a read timeout as a terminal failure after one request. This historical definition is retained for discrepancy testing and must never be read as the current retry policy. RS-2026-09 permits one same-key retry after a connection failure or provider 503. The operational boundary is still two seconds per attempt; a second failure leaves the draft recoverable. The local audit identifies the attempted rules version and correlation ID so the historical and current policies are not conflated. A customer-facing result never invents a band when the final provider outcome remains unknown."),
        ("RiskSignal", "Version ownership", "Questionnaire version Q3 is selected by the platform before any external call. RiskSignal applies the named RS-2026-09 scoring rules and echoes that rules version in its response. D-2026-09 dictionary labels are platform-owned and need not match provider display wording. A rules version change is an explicit provider contract change; it cannot silently reinterpret an already accepted historical profile. An old Q2 result remains readable with its original questionnaire and rules references, while a new Q2 submission is rejected as outdated. The risk integration team owns mapping and validation, and product owners approve displayed explanations."),
        ("RiskSignal", "Failure ownership", "A malformed request is a platform validation defect, a 503 is provider availability, a missing response field is a provider contract defect, and a failed PostgreSQL acceptance is a platform persistence defect. Each case has a different recovery path and audit status. Operations uses correlationId to locate the attempt, idempotencyKey to avoid duplicate acceptance, and providerAssessmentId only when a provider result exists. None of these IDs doubles as a customer identifier. The platform retains the prior unexpired ACTIVE summary during reassessment failure and exposes a clear retry action rather than a fabricated accepted result."),
        ("MarketPulse", "Quote contract example", "GET /quotes/XS0000000001 can return bid 101.25, ask 101.40, quoteCurrency PLN, session OPEN, instrumentRisk MEDIUM and asOf 2026-10-01T12:00:00Z. The UI presents both prices and the timestamp because a quote without time context can mislead a trading decision. MEDIUM is a volatility descriptor for the instrument reference; it cannot be mapped to investor band R2 by matching English words. The provider owns quote value and instrument metadata; the platform owns display, staleness warnings and order eligibility. A malformed negative bid is refused even if the session remains OPEN."),
        ("MarketPulse", "Delisted instrument", "A 404 for an instrument reference prevents a new quote or order for that identifier, but a saved watchlist entry can remain as historical context. The browse view identifies the missing instrument rather than presenting the last cached quote as current. A changed instrument category is versioned reference information and cannot retroactively change a previously accepted investor profile. Market-data operations investigate the provider response. No RiskSignal call is made merely because a quote disappeared, and the risk submission integration test must observe zero MarketPulse calls."),
        ("MarketPulse", "Rate limit and retry", "A 429 response with retry-after is not the same as a 503 transient outage. The quote view should show throttling and avoid an immediate retry storm. A single 503 read retry is allowed because GET /quotes is read-only; the same assumption is not transferable to a reservation POST. The local stub records each quote call independently from risk requests. A quote retry may preserve correlationId for troubleshooting, but it does not reuse the profile idempotency key or create an assessment audit. Operators should compare service-specific counters before attributing a load spike to risk profiling."),
        ("MarketPulse", "Market status separation", "MarketPulse provides a venue session and an instrument-risk descriptor, while the platform maintains investor status, questionnaire answers and accepted profile status. A HALTED venue is an order precondition, not an investor assessment status. An operational incident with severity S2 can make quote browsing unavailable without turning a customer's risk band into R2 or expiring a valid profile. The integration status mockup places these labels near one another specifically to test source selection. A downstream document should cite the correct service and dictionary cell for each meaning."),
        ("CustodyBridge", "Reservation example", "A synthetic order O-901 on account ACC-100 may request amount 101.40 PLN using reservationKey reserve-O-901 and a separate correlationId. CustodyBridge returns reservationId cb-reserve-O-901 with RESERVED status. The platform must match the returned reservation to the pending order before advancing its state; an unrelated reservation cannot satisfy a different order. Repeating the exact request with the same reservationKey is safe only under the provider's idempotency contract. A changed amount with the same key is a conflict. Profile submission has no accountRef, orderRef or reservationKey and never touches this contract."),
        ("CustodyBridge", "Balance snapshot", "Available cash is reported in account currency with balanceAsOf. A stale balance is labelled stale and should prompt a new check before reservation. A positive availableCash amount does not guarantee an order will settle, because the later reservation may be rejected or the custody account may become BLOCKED. The account balance belongs to the trading lifecycle and does not stand in for loss tolerance or liquidity need in a Q3 questionnaire. The investor supplies those answers directly. RiskSignal never receives a cash balance from the fixture's risk-profile request."),
        ("CustodyBridge", "Settlement replay", "A settlement event for O-901 includes settlementId set-901 and settledAt in UTC. The order adapter must record settlementId before reporting SETTLED, so a repeated callback can be detected. A second event with the same settlementId and different orderRef is a conflict requiring operations review, not another successful order. The accepted risk profile remains immutable; neither settlement nor reversal changes the providerAssessmentId of a prior assessment. This separation lets later ticket selection distinguish a trading event fix from the risk-profile history story even when both use shared account references."),
        ("CustodyBridge", "Outage ownership", "When CustodyBridge is unavailable, new reservation attempts stop and the order view identifies the custody integration as owner. A previously accepted profile may still be displayed in the profile history view. The backend's risk workflow is wired only to RiskSignalClient, so a CustodyBridge outage cannot become an assessment error unless shared infrastructure itself fails. The local stub's call log supplies a direct negative control for this claim. An integration test should inspect the custody counter after both a successful risk submission and a RiskSignal failure, expecting zero in each case."),
    ]
    return [(f"contract-{index + 1:02d}", f"{service}: {title}", prose) for index, (service, title, prose) in enumerate(cases)]


def dictionary_rows():
    rows = []
    for group, title, owner, ticket, *rest in DICTIONARIES:
        definitions = rest[:4]
        exception, consumer = rest[4:]
        for position, definition in enumerate(definitions, 1):
            code, label, meaning, transitions = definition.split("|")
            identifier = f"DICT-{group.upper()}-{position:02d}"
            applicability = "Current Q3" if group in {"experience-level", "investment-horizon", "loss-tolerance", "liquidity-need", "risk-band", "questionnaire-version", "consent-type"} else "Platform-wide"
            if "Historical" in label or "Planned" in label:
                applicability = label.split()[0]
            cells = [identifier, f"{title}: {code} — {label}", f"{meaning} The stable code is {code}; the display label is for readers and may be localized. A consumer must persist the code and the dictionary revision, never infer a code from a translated label.", f"Owner: {owner}. Effective: 2026-09-01 in revision D-2026-09. Applicability: {applicability}. Allowed next values: {transitions}. An unlisted transition requires an explicit versioned change rather than a silent update.", f"{exception} {consumer} A boundary or invalid input must yield a field-level rejection without modifying an accepted profile.", f"{ticket} supplies the feature context. This record is distinct from the similarly named investor, instrument, and operational classifications. A historical value remains readable with its original version but cannot be assumed current."]
            rows.append((identifier, cells))
    return rows


def service_rows():
    rows = []
    for service in SERVICES:
        for index, (field, contract, failure) in enumerate(service["fields"], 1):
            identifier = f"SVC-{service['name'].upper()}-{index:02d}"
            cells = [identifier, service["name"], f"{field}: {contract}. This field belongs to {service['endpoint']} and is interpreted by {service['consumer']} for {service['purpose']}.", f"Constraint and failure: {failure}. Correlation ID is propagated through the local request, response and audit. A validation failure is owned by {service['owner']} and must not be converted to a successful result.", f"Timeout: {service['timeout']}. Retry: {service['retry']}. The deterministic local base is {service['mock']}. Its endpoint and status are fixed fixture contracts, not public production services.", f"Risk dependency: {service['dependency']}. {service['ticket']} owns this contract area. A provider response is only input to platform validation; persistence and customer presentation remain platform decisions."]
            rows.append((identifier, cells))
    return rows


def story_rows():
    rows = []
    variants = [
        ("primary", "Start from the current Q3 screen; show the owner, saved version and next action together.", "The acceptance path uses seeded investor INV-100 and checks persisted state after a fresh request."),
        ("return", "Reopen the same journey after a browser reload and show any changed version before action.", "Acceptance repeats the request with the same identity and confirms that no second accepted result appears."),
        ("failure", "Show the exception beside the affected action and retain a recovery route to the draft.", "Acceptance asserts the stated failure without a call to unrelated providers or a false active profile."),
    ]
    for number, title, product, implementation, exception, check in STORIES:
        for variant_index, (variant, journey, acceptance) in enumerate(variants, 1):
            identifier = f"STORY-{number}-{variant_index}"
            status = "planned" if number in {"2018", "2020"} else "partial" if number == "2013" else "implemented"
            if number == "2019" and variant == "return":
                status = "historical discrepancy"
            cells = [identifier, f"As an investor or operations reviewer, I want to {title.lower()} so that I can understand the outcome. The phrase 'review the current profile' also occurs in trading context and does not prove this rule.", f"Product behavior: {product} {journey} The screen cites the applicable dictionary code and distinguishes a saved draft from an accepted profile.", f"Implementation behavior: {implementation} Use stable draft/profile IDs, a Q3 answer snapshot and RS-2026-09 provider provenance. {check}", f"Acceptance: {acceptance} {exception} {check} A failed case never fabricates a provider proposal or silently replaces a prior assessment.", f"TICKET-{number}; status {status}; Q3 / RS-2026-09. The relevant dictionary entries and RiskSignal contract define codes and request fields. Screen references: questionnaire, answer-validation, assessment-result and profile-history."]
            rows.append((identifier, cells))
    return rows


def render_screen(path, details):
    title, subtitle, *items = details
    image = Image.new("RGB", (1100, 650), "#f3f7f6")
    draw = ImageDraw.Draw(image)
    heading = ImageFont.truetype(str(FONT_PATH), 34)
    normal = ImageFont.truetype(str(FONT_PATH), 22)
    small = ImageFont.truetype(str(FONT_PATH), 18)
    draw.rectangle((0, 0, 1100, 94), fill="#153d3a")
    draw.text((44, 27), "Northstar Investment · synthetic", font=heading, fill="white")
    draw.text((44, 127), title, font=heading, fill="#173c38")
    draw.text((46, 177), subtitle, font=normal, fill="#526c67")
    for index, item in enumerate(items):
        top = 230 + index * 72
        draw.rounded_rectangle((42, top, 1058, top + 58), radius=12, fill="white", outline="#b8cec7", width=2)
        draw.text((64, top + 17), item, font=normal, fill="#183b37")
    draw.text((45, 607), "Fixture mockup · fictional data · 1100 × 650", font=small, fill="#687d77")
    image.save(path, "JPEG", quality=90, subsampling=0, optimize=False, progressive=False)


def make_images():
    if not FONT_PATH.exists():
        raise RuntimeError(f"Required fixed rendering font is missing: {FONT_PATH}")
    for screen, details in SCREENS.items():
        source = FULL / "assets" / f"{screen}.jpg"
        source.parent.mkdir(parents=True, exist_ok=True)
        render_screen(source, details)
        target = FULL_HTML / "attachments" / "8421" / f"{screen}-screen.jpg"
        write(target, bytes_at(source))
    for screen in ("questionnaire", "assessment-result"):
        source = FULL / "assets" / f"{screen}.jpg"
        write(QUICK / "assets" / f"{screen}.jpg", bytes_at(source))
        write(QUICK_HTML / "attachments" / "8421" / f"{screen}-screen.jpg", bytes_at(source))


def make_quick(base_url):
    url = f"{base_url}/risk-profiling.html"
    intro = "A concise synthetic profile journey for INV-100. Review the current profile before starting a new draft. Review the current profile after recovery as well."
    rows = []
    for identifier, fact, condition, ticket, disposition in QUICK_FACTS:
        rows.append((identifier, [identifier, fact, condition, ticket, "Current" if disposition == "included" else "Planned; uncertain", "The visible rule is test evidence; the image is only a screen illustration."]))
    markdown, html = frame("Risk profiling quick source", "investment-platform/quick-risk-profiling", url, rows, ["ID", "Rule", "Condition or exception", "Ticket", "Status", "Evidence note"], intro, [("questionnaire", "The questionnaire shows selected codes, consent and the next action."), ("assessment-result", "The accepted result shows its band, reasons and rules revision.")])
    markdown += "\nRetry once.\n\n**No provider call** occurs for an incomplete draft. Sławomir's złoty example is synthetic. RiskSignal &amp; platform share a correlation ID. Q3\u00a0consent is required. A failed reassessment leaves the prior unexpired profile active. A failed reassessment leaves the prior unexpired profile active until its original expiry.\n\nUncertainty: automatic reconciliation of an orphan audit is planned; current inclusion requires a human review decision.\n"
    html = html.replace("</main>", "<p>Retry once.</p><p><strong>No provider call</strong> occurs for an incomplete draft. Sławomir's złoty example is synthetic. RiskSignal &amp; platform share a correlation ID. Q3&nbsp;consent is required. A failed reassessment leaves the prior unexpired profile active. A failed reassessment leaves the prior unexpired profile active until its original expiry.</p><p>Uncertainty: automatic reconciliation of an orphan audit is planned; current inclusion requires a human review decision.</p></main>")
    write(QUICK / "risk-profiling.md", markdown)
    write(QUICK_HTML / "risk-profiling.html", html)
    write(QUICK_HTML / "index.html", '<!doctype html><html lang="en"><meta charset="utf-8"><title>Quick source</title><a href="risk-profiling.html">Risk profiling quick source</a></html>\n')
    return rows


def make_full(base_url):
    pages = [
        ("01-dictionaries", "Shared dictionaries and versions", "investment-platform/dictionaries", dictionary_rows(), ["ID", "Code and label", "Business meaning", "Owner and version", "Invalid case and consumer", "Scope and provenance"], "Versioned platform dictionaries distinguish investor risk, instrument risk and operational severity. Q1 and Q2 definitions are historical; Q3 is current; Q4 remains planned.", [("dictionary-admin", "Dictionary administration displays effective Q3 codes beside the retained Q2 revision."), ("questionnaire", "The questionnaire consumes current experience, horizon, tolerance and liquidity codes.")], dictionary_notes()),
        ("02-external-services", "External service catalog", "investment-platform/external-services", service_rows(), ["ID", "Service", "Field and operation", "Constraint and failure", "Timeout and local setup", "Ownership and scope"], "Exactly three fictional business services exist: RiskSignal, MarketPulse and CustodyBridge. Risk profiling calls RiskSignal only. Local PostgreSQL and MongoDB are internal stores, not external business services. Dependency table: risk profiling to RiskSignal; quote browsing to MarketPulse; order reservation and settlement to CustodyBridge. No other provider edge is implied by a shared account reference or similar risk term.", [("integration-status", "Integration status names three independent providers and keeps operational severity separate from investor risk."), ("assessment-result", "A proposed RiskSignal band becomes an accepted profile only after platform validation and persistence.")], service_notes()),
        ("03-risk-profiling", "TICKET-2000 risk profiling epic", "investment-platform/risk-profiling", story_rows(), ["ID", "User story", "Product solution", "Implementation solution", "Acceptance and exception", "Ticket and status"], "TICKET-2000 covers a recoverable Q3 draft, validated consent, idempotent RiskSignal submission, accepted profile history and expiry. Trading and custody are out of scope. A failed reassessment leaves the prior unexpired profile active.", [("questionnaire", "The current Q3 questionnaire exposes required answers and CP-3 consent."), ("answer-validation", "An invalid 5.1 percent answer is rejected before any provider call."), ("assessment-result", "The accepted result displays R2 with reasons and RS-2026-09 provenance."), ("profile-history", "Historical results remain readable with their original questionnaire and rules versions.")], []),
    ]
    output = []
    for slug, title, source_id, rows, headers, intro, visuals, notes in pages:
        markdown, html = frame(title, source_id, f"{base_url}/{slug}.html", rows, headers, intro, visuals, notes)
        if slug == "03-risk-profiling":
            markdown += "\nCurrent correction: exactly 5 percent maps to L5; historical pre-fix behavior accepted free-text 5.1 as a tolerance input and is not current.\n\nReview pending for orphan audit.\n\nUnresolved product ambiguity: whether an expired profile may be displayed on the trading confirmation screen needs a recorded product decision; this fixture excludes that claim.\n"
            html = html.replace("</main>", "<p>Current correction: exactly 5 percent maps to L5; historical pre-fix behavior accepted free-text 5.1 as a tolerance input and is not current.</p><p>Review required for orphan audit.</p><p>Unresolved product ambiguity: whether an expired profile may be displayed on the trading confirmation screen needs a recorded product decision; this fixture excludes that claim.</p></main>")
        write(FULL / f"{slug}.md", markdown)
        write(FULL_HTML / f"{slug}.html", html)
        output.append((slug, source_id, rows, len(markdown)))
    links = "".join(f'<li><a href="{slug}.html">{slug}</a></li>' for slug, *_ in output)
    write(FULL_HTML / "index.html", f'<!doctype html><html lang="en"><meta charset="utf-8"><title>Investment platform sources</title><h1>Investment platform sources</h1><ul>{links}</ul></html>\n')
    return output


def json_line(path, records):
    write(path, "".join(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n" for record in records))


def make_reference(full_pages, quick_rows, full_url, quick_url):
    page_map = {source_id: {"source_url": f"{full_url}/{slug}.html", "html_path": f"data/test_data_2_html/{slug}.html", "markdown_path": f"data/test_data_2/{slug}.md"} for slug, source_id, _, _ in full_pages}
    quick_map = {"investment-platform/quick-risk-profiling": {"source_url": f"{quick_url}/risk-profiling.html", "html_path": "data/test_data_2_quick_html/risk-profiling.html", "markdown_path": "data/test_data_2_quick/risk-profiling.md"}}
    write(REFERENCE / "source-page-map-full.json", json.dumps({"schema_version": 1, "pages": page_map}, indent=2) + "\n")
    write(REFERENCE / "source-page-map-quick.json", json.dumps({"schema_version": 1, "pages": quick_map}, indent=2) + "\n")
    cases = []
    facts = []
    for slug, source_id, rows, _ in full_pages:
        location = page_map[source_id]
        for index, (identifier, cells) in enumerate(rows):
            if index >= 16:
                continue
            quote = cells[2] if slug != "03-risk-profiling" else cells[4]
            target = quote.split(". ", 1)[0] + "."
            claim = target
            cases.append({"case_id": f"C-{slug[:2]}-{index + 1:02d}", "source_id": source_id, "markdown_path": location["markdown_path"], "html_path": location["html_path"], "claim": claim, "evidence_quote": quote, "target_text": target, "expected_behavior": "text_fragment", "reason": "Specific solution or acceptance cell supports this claim; the generic story does not.", "forbidden_fragments": [identifier, "assets/", "attachments/", "screen"]})
    ids = {"dictionaries": "investment-platform/dictionaries", "external-services": "investment-platform/external-services", "risk-profiling": "investment-platform/risk-profiling"}
    for index, (section, row_id, claim, quote, condition, exception, ticket) in enumerate(FULL_EXPECTATIONS, 1):
        source_id = ids[section]
        product_version = "D-2026-09" if section == "dictionaries" else "Q3/RS-2026-09" if section == "risk-profiling" else "RS-2026-09" if row_id.startswith("SVC-RISKSIGNAL") else "fixture-contract-v1"
        facts.append({"fact_id": f"F-FULL-{index:02d}", "source_id": source_id, "markdown_path": page_map[source_id]["markdown_path"], "row_id": row_id, "source_quote": quote, "claim": claim, "conditions": condition, "exceptions": exception, "status": "partial" if ticket == "TICKET-2013" else "current", "version": product_version, "fixture_revision": REVISION, "tickets": [ticket], "dependency_tickets": ["TICKET-2000"] if section == "risk-profiling" else [], "expected_disposition": "included", "human_reviewed": False})
    risk = page_map["investment-platform/risk-profiling"]
    cases.append({"case_id": "C-NEG-01", "source_id": "investment-platform/risk-profiling", "markdown_path": risk["markdown_path"], "html_path": risk["html_path"], "claim": "Orphan audit review is pending.", "evidence_quote": "Review pending for orphan audit.", "target_text": "Review pending for orphan audit.", "expected_behavior": "local_evidence", "reason": "The HTML mirror deliberately changes this isolated phrase; the original Markdown evidence remains available.", "forbidden_fragments": ["Review required for orphan audit."]})
    for case_id, source_id, claim, quote in [
        ("C-MARKET-01", "investment-platform/external-services", "Instrument risk is not the investor band.", "instrumentRisk: issuer-owned volatility descriptor"),
        ("C-CUSTODY-01", "investment-platform/external-services", "Order reservation has its own idempotency key.", "reservationKey: stable order idempotency key"),
        ("C-OPERATIONAL-01", "investment-platform/dictionaries", "S2 is an operational severity.", "Material feature degraded"),
    ]:
        location = page_map[source_id]
        cases.append({"case_id": case_id, "source_id": source_id, "markdown_path": location["markdown_path"], "html_path": location["html_path"], "claim": claim, "evidence_quote": quote, "target_text": quote, "expected_behavior": "text_fragment", "reason": "Similar risk and status terms must retain their service or dictionary scope.", "forbidden_fragments": ["investor risk_band", "assets/", "attachments/"]})
    quick = quick_map["investment-platform/quick-risk-profiling"]
    for index, (identifier, fact, condition, ticket, disposition) in enumerate(QUICK_FACTS, 1):
        cases.append({"case_id": f"C-Q-{index:02d}", "source_id": "investment-platform/quick-risk-profiling", "markdown_path": quick["markdown_path"], "html_path": quick["html_path"], "claim": fact, "evidence_quote": fact, "target_text": fact, "expected_behavior": "text_fragment" if disposition == "included" else "excluded", "reason": "Quick fact is visible in its own rule cell; the planned item requires human review." if disposition == "included" else "Unimplemented reconciliation is excluded.", "forbidden_fragments": ["assets/", "attachments/", "screen"]})
    for identifier, claim, quote, condition, ticket, disposition in QUICK_EXPECTATIONS:
        facts.append({"fact_id": identifier, "source_id": "investment-platform/quick-risk-profiling", "markdown_path": quick["markdown_path"], "row_id": identifier, "source_quote": quote, "claim": claim, "conditions": condition, "exceptions": condition, "status": "current" if disposition == "included" else "planned", "version": "Q3/RS-2026-09", "fixture_revision": REVISION, "tickets": [ticket], "expected_disposition": disposition, "human_reviewed": False})
    cases.append({"case_id": "C-SHORT-01", "source_id": "investment-platform/quick-risk-profiling", "markdown_path": quick["markdown_path"], "html_path": quick["html_path"], "claim": "Retry once.", "evidence_quote": "Retry once.", "target_text": "Retry once.", "expected_behavior": "text_fragment", "reason": "A short unique rule must remain linkable.", "max_encoded_fragment_bytes": 32})
    for case_id, claim, quote, target, reason in [
        ("C-UNICODE-01", "A fictional złoty example names Sławomir.", "Sławomir's złoty example is synthetic.", "Sławomir's złoty example is synthetic.", "Unicode names and currency characters remain visible."),
        ("C-ENTITY-01", "RiskSignal and platform share a correlation ID.", "RiskSignal &amp; platform share a correlation ID.", "RiskSignal & platform share a correlation ID.", "An HTML entity decodes in visible text."),
        ("C-NBSP-01", "Q3 consent is required.", "Q3\u00a0consent is required.", "Q3\u00a0consent is required.", "A nonbreaking space remains part of the visible rule."),
        ("C-FORMAT-01", "Incomplete drafts make no provider call.", "**No provider call** occurs for an incomplete draft.", "No provider call", "Inline formatting preserves the visible words."),
        ("C-REPEAT-01", "Review the current profile before starting.", "Review the current profile before starting a new draft.", "Review the current profile", "The same opening appears again after recovery and needs context."),
        ("C-DUPLICATE-01", "Failed reassessment retains the active profile.", "A failed reassessment leaves the prior unexpired profile active.", "A failed reassessment leaves the prior unexpired profile active.", "An exact duplicate must not be counted as a new fact."),
        ("C-SCOPED-01", "The prior active profile lasts only to original expiry.", "A failed reassessment leaves the prior unexpired profile active until its original expiry.", "until its original expiry", "The scoped variant adds a real condition to the duplicated core claim."),
    ]:
        cases.append({"case_id": case_id, "source_id": "investment-platform/quick-risk-profiling", "markdown_path": quick["markdown_path"], "html_path": quick["html_path"], "claim": claim, "evidence_quote": quote, "target_text": target, "expected_behavior": "text_fragment", "reason": reason, "forbidden_fragments": ["assets/", "attachments/"]})
    dictionary = page_map["investment-platform/dictionaries"]
    cases.append({"case_id": "C-IMAGE-ONLY-01", "source_id": "investment-platform/dictionaries", "markdown_path": dictionary["markdown_path"], "html_path": dictionary["html_path"], "claim": "Navigation artwork proves a risk rule.", "evidence_quote": "![decorative navigation](assets/dictionary-admin.jpg)", "target_text": "decorative navigation", "expected_behavior": "excluded", "reason": "An image-only source block cannot support a text claim.", "forbidden_fragments": ["decorative navigation", "dictionary-admin.jpg", "attachments/"]})
    json_line(REFERENCE / "citation-cases.jsonl", cases)
    json_line(REFERENCE / "expected-facts.jsonl", facts)
    json_line(REFERENCE / "discrepancies.jsonl", [
        {"id": "D-01", "kind": "historical-code-rule", "source_id": "investment-platform/risk-profiling", "historical": "Before TICKET-2019, free-text 5.1 was accepted as a tolerance input.", "current": "Current Q3 rejects 5.1 percent free text.", "expected_disposition": "historical_only", "human_reviewed": False},
        {"id": "D-02", "kind": "mirror-negative", "source_id": "investment-platform/risk-profiling", "markdown": "Review pending for orphan audit.", "html": "Review required for orphan audit.", "expected_disposition": "local_evidence", "human_reviewed": False},
        {"id": "D-03", "kind": "unresolved-product-ambiguity", "source_id": "investment-platform/risk-profiling", "question": "May an expired profile appear on trading confirmation?", "expected_disposition": "excluded_pending_review", "human_reviewed": False},
        {"id": "D-04", "kind": "wrong-plausible-alternative", "source_id": "investment-platform/external-services", "claim": "MarketPulse instrumentRisk MEDIUM is the investor's accepted R2 band.", "expected_disposition": "excluded", "reason": "Instrument and investor risk are different entities.", "human_reviewed": False},
        {"id": "D-05", "kind": "wrong-plausible-alternative", "source_id": "investment-platform/external-services", "claim": "CustodyBridge must reserve funds before RiskSignal can assess a profile.", "expected_disposition": "excluded", "reason": "Risk profiling has no custody dependency.", "human_reviewed": False},
    ])
    return cases, facts


def make_manifest(full_pages, cases, facts, full_url, quick_url):
    roots = [FULL, FULL_HTML, QUICK, QUICK_HTML, REFERENCE]
    files = {}
    for root in roots:
        for path in root.rglob("*"):
            if path.is_file() and path.name != "manifest.json":
                files[path.relative_to(ROOT).as_posix()] = digest(bytes_at(path))
    manifest = {
        "schema_version": 1, "fixture_revision": REVISION, "source_url_bases": {"full": full_url, "quick": quick_url},
        "pages": [{"slug": slug, "source_id": source_id, "markdown_path": f"data/test_data_2/{slug}.md", "html_path": f"data/test_data_2_html/{slug}.html", "characters": size, "records": len(rows)} for slug, source_id, rows, size in full_pages] + [{"slug": "risk-profiling", "source_id": "investment-platform/quick-risk-profiling", "markdown_path": "data/test_data_2_quick/risk-profiling.md", "html_path": "data/test_data_2_quick_html/risk-profiling.html", "characters": len((QUICK / "risk-profiling.md").read_text(encoding="utf-8")), "records": len(QUICK_FACTS)}],
        "citation_case_count": len(cases), "expected_fact_count": len(facts), "file_sha256": dict(sorted(files.items())),
        "toolchain": {"python": sys.version.split()[0], "pillow": Image.__version__, "font_path": str(FONT_PATH), "font_sha256": digest(bytes_at(FONT_PATH)), "jpeg": "quality=90,subsampling=0,baseline,1100x650", "java_target": "17", "spring_boot": "3.5.16", "maven_wrapper": "3.9.16", "angular": "21.2.25", "node_tested": "24.21.0", "postgresql": "17.7", "mongodb": "8.0.17"},
        "build_commands": ["python scripts/test_data_2/build_fixture.py", "python scripts/test_data_2/build_history.py", "python scripts/test_data_2/validate_fixture.py"],
        "intentional_defects": ["D-01", "D-02", "D-03", "D-04", "D-05"], "semantic_expectations_human_reviewed": False,
    }
    write(REFERENCE / "manifest.json", json.dumps(manifest, ensure_ascii=False, sort_keys=True, indent=2) + "\n")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--full-port", type=int, default=8766)
    parser.add_argument("--quick-port", type=int, default=8767)
    args = parser.parse_args()
    prepare_roots()
    make_images()
    full_url = f"http://{args.host}:{args.full_port}"
    quick_url = f"http://{args.host}:{args.quick_port}"
    full_pages = make_full(full_url)
    quick_rows = make_quick(quick_url)
    cases, facts = make_reference(full_pages, quick_rows, full_url, quick_url)
    make_manifest(full_pages, cases, facts, full_url, quick_url)
    for slug, _, rows, size in full_pages:
        print(f"{slug}: {len(rows)} records, {size} characters")
    print(f"quick: {len(quick_rows)} records; {len(cases)} citation cases; {len(facts)} expected facts")


if __name__ == "__main__":
    main()
