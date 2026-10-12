import hashlib
import html
import json
import re
import subprocess
import tempfile
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import quote

from PIL import Image


ROOT = Path(__file__).resolve().parents[2]
REFERENCE = ROOT / "data" / "test_data_2_reference"
FULL = ROOT / "data" / "test_data_2"
QUICK = ROOT / "data" / "test_data_2_quick"
HISTORY = ROOT / "data" / "investment_platform_history"
SNAPSHOT = ROOT / "data" / "investment_platform"


def check(condition, message):
    if not condition:
        raise AssertionError(message)


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def read_lines(path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def normalize(content):
    return " ".join(html.unescape(content).split())


class MirrorParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.visible = []
        self.rows = {}
        self.images = []
        self.row = None
        self.cell = None
        self.hidden = 0

    def handle_starttag(self, tag, attrs):
        attributes = dict(attrs)
        if tag in {"script", "style"}:
            self.hidden += 1
        if tag == "img":
            self.images.append(attributes["src"])
        if tag == "tr" and attributes.get("id"):
            self.row = attributes["id"]
            self.rows[self.row] = []
        if tag in {"td", "th"} and self.row:
            self.cell = []

    def handle_endtag(self, tag):
        if tag in {"script", "style"}:
            self.hidden -= 1
        if tag in {"td", "th"} and self.cell is not None and self.row:
            self.rows[self.row].append(normalize("".join(self.cell)))
            self.cell = None
        if tag == "tr":
            self.row = None

    def handle_data(self, data):
        if self.hidden:
            return
        self.visible.append(data)
        if self.cell is not None:
            self.cell.append(data)


def html_parser(path):
    parser = MirrorParser()
    parser.feed(path.read_text(encoding="utf-8"))
    return parser


def metadata(markdown):
    parts = markdown.split("---", 2)
    check(len(parts) == 3, "Missing front matter")
    return dict(line.split(": ", 1) for line in parts[1].strip().splitlines())


def markdown_rows(content):
    rows = {}
    for line in content.splitlines():
        if not line.startswith("| ") or line.startswith("| ---") or line.startswith("| ID "):
            continue
        cells = [normalize(cell.strip().replace("\\|", "|")) for cell in line.strip("| ").split(" | ")]
        if cells and re.fullmatch(r"(?:DICT|SVC|STORY|QF)\S+", cells[0]):
            rows[cells[0]] = cells
    return rows


def markdown_images(content):
    inline = re.findall(r"!\[[^]]*\]\(([^)]+)\)", content)
    references = re.findall(r"^\[[^]]+\]:\s+(\S+\.jpg)$", content, flags=re.MULTILINE)
    raw = re.findall(r"<img\s+src=\"([^\"]+)\"", content)
    return inline + references + raw


def validate_page_map(path, expected_count):
    mapping = read_json(path)
    check(mapping["schema_version"] == 1 and len(mapping["pages"]) == expected_count, "Invalid page map")
    for source_id, page in mapping["pages"].items():
        markdown_path = ROOT / page["markdown_path"]
        html_path = ROOT / page["html_path"]
        check(markdown_path.is_file() and html_path.is_file(), f"Missing mapped page {source_id}")
        source = markdown_path.read_text(encoding="utf-8")
        properties = metadata(source)
        check(properties["source_id"] == source_id and properties["source_url"] == page["source_url"], f"Source metadata mismatch {source_id}")
        check(properties["source_system"] == "local-html" and properties["source_revision"] == "investment-fixture-v1", f"Source revision mismatch {source_id}")
        mirror = html_parser(html_path)
        rows = markdown_rows(source)
        check(rows == mirror.rows, f"Markdown/HTML table cells differ for {source_id}")
        for _, heading, prose in re.findall(r"^### ([^\n]+): ([^\n]+)\n\n([^\n]+)", source, flags=re.MULTILINE):
            check(normalize(prose) in normalize("".join(mirror.visible)), f"Operational note differs for {source_id}: {heading}")
        for name in markdown_images(source):
            check(name.startswith("assets/") and ".." not in Path(name).parts, f"Unsafe Markdown image {name}")
            check((markdown_path.parent / name).is_file(), f"Missing Markdown image {name}")
        for name in mirror.images:
            check(name.startswith("attachments/8421/") and ".." not in Path(name).parts, f"Unsafe HTML image {name}")
            check((html_path.parent / name).is_file(), f"Missing HTML image {name}")
        check(all("assets/" not in image for image in mirror.images), "Mirror reused Markdown asset path")
    return mapping


def validate_assets():
    paths = []
    for name in ("test_data_2", "test_data_2_html", "test_data_2_quick", "test_data_2_quick_html"):
        folder = ROOT / "data" / name
        asset_roots = [item for item in (folder / "assets", folder / "attachments") if item.exists()]
        for asset_root in asset_roots:
            check(all(path.suffix.lower() == ".jpg" for path in asset_root.rglob("*") if path.is_file()), f"Non-JPEG asset under {asset_root}")
        for path in folder.rglob("*"):
            if not path.is_file() or path.suffix.lower() not in {".jpg", ".jpeg"}:
                continue
            with Image.open(path) as image:
                check(image.format == "JPEG" and image.size == (1100, 650), f"Invalid JPEG {path}")
                image.load()
                extrema = image.convert("L").getextrema()
                check(extrema[1] - extrema[0] > 100, f"Unreadable low-contrast image {path}")
            paths.append(path)
        check(not list(folder.rglob("*.svg")) and not list(folder.rglob("*.png")) and not list(folder.rglob("*.webp")), f"Unexpected image format under {folder}")
    unique = {sha(path) for path in FULL.glob("assets/*.jpg")}
    check(len(unique) >= 6, "Fewer than six distinct mockups")
    return len(paths), len(unique)


def validate_references(full_map, quick_map):
    pages = full_map["pages"] | quick_map["pages"]
    cases = read_lines(REFERENCE / "citation-cases.jsonl")
    facts = read_lines(REFERENCE / "expected-facts.jsonl")
    known_tickets = read_json(REFERENCE / "ticket-map.json")["tickets"]
    check(len(cases) >= 24 and len(facts) >= 50, "Reference package is too small")
    check(len({case["case_id"] for case in cases}) == len(cases), "Duplicate citation case ID")
    check(len({fact["fact_id"] for fact in facts}) == len(facts), "Duplicate fact ID")
    for case in cases:
        page = pages[case["source_id"]]
        check(case["markdown_path"] == page["markdown_path"] and case["html_path"] == page["html_path"], f"Case path mismatch {case['case_id']}")
        markdown = (ROOT / page["markdown_path"]).read_text(encoding="utf-8")
        visible = normalize("".join(html_parser(ROOT / page["html_path"]).visible))
        check(case["evidence_quote"] in markdown, f"Missing evidence quote {case['case_id']}")
        behavior = case["expected_behavior"]
        check(behavior in {"text_fragment", "local_evidence", "excluded"}, "Unknown citation behavior")
        target = normalize(case["target_text"])
        if behavior == "text_fragment":
            check(target in visible, f"Target absent from mirror {case['case_id']}")
        if behavior == "local_evidence":
            check(target not in visible, f"Negative target unexpectedly present {case['case_id']}")
        if "max_encoded_fragment_bytes" in case:
            check(len(quote(case["target_text"], safe="").encode("ascii")) <= case["max_encoded_fragment_bytes"], f"Short bound violated {case['case_id']}")
    for fact in facts:
        page = pages[fact["source_id"]]
        check(fact["markdown_path"] == page["markdown_path"], f"Fact path mismatch {fact['fact_id']}")
        rows = markdown_rows((ROOT / page["markdown_path"]).read_text(encoding="utf-8"))
        check(fact["row_id"] in rows and normalize(fact["source_quote"]) in " ".join(rows[fact["row_id"]]), f"Fact quote missing from its row {fact['fact_id']}")
        check(fact["expected_disposition"] in {"included", "excluded"}, f"Fact disposition invalid {fact['fact_id']}")
        check(fact["claim"] and fact["conditions"] and fact["exceptions"] and fact["status"] and fact["version"], f"Incomplete semantic expectation {fact['fact_id']}")
        check(all(ticket in known_tickets for ticket in fact["tickets"]), f"Unknown fact ticket {fact['fact_id']}")
    discrepancies = read_lines(REFERENCE / "discrepancies.jsonl")
    check({item["id"] for item in discrepancies} == {"D-01", "D-02", "D-03", "D-04", "D-05"}, "Missing intentional discrepancy")
    return len(cases), len(facts)


def validate_history():
    manifest = read_json(HISTORY / "manifest.json")
    bundle = HISTORY / "investment-platform.bundle"
    check(sha(bundle) == manifest["bundle_sha256"], "Bundle hash mismatch")
    commits = manifest["commits"]
    check(len(commits) >= 18 and len(commits) == manifest["commit_count"], "Insufficient Git history")
    check(sum(item["ticket"].startswith("TICKET-2") for item in commits) >= 10, "Too few risk commits")
    check(sum(item["ticket"].startswith("TICKET-3") for item in commits) >= 4, "Too few unrelated commits")
    check(all(re.match(r"^TICKET-\d{4} ", item["subject"]) and item["changed_paths"] for item in commits), "Invalid or empty commit")
    check(len({item["ticket"] for item in commits}) < len(commits), "No multi-commit ticket")
    snapshot = {path.relative_to(SNAPSHOT).as_posix(): sha(path) for path in SNAPSHOT.rglob("*") if path.is_file()}
    check(snapshot == manifest["file_sha256"], "Readable snapshot differs from history manifest")
    temporary_root = ROOT / ".docgen" / "fixtures"
    temporary_root.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="fixture-validation-", dir=temporary_root) as work:
        folder = Path(work) / "clone"
        result = subprocess.run(["git", "clone", "--quiet", str(bundle), str(folder)], text=True, capture_output=True)
        check(result.returncode == 0, f"Bundle clone failed: {result.stderr}")
        head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=folder, text=True).strip()
        tree = subprocess.check_output(["git", "rev-parse", "HEAD^{tree}"], cwd=folder, text=True).strip()
        check(head == manifest["head"] and tree == manifest["tree"], "Bundle HEAD/tree mismatch")
        cloned = {path.relative_to(folder).as_posix(): sha(path) for path in folder.rglob("*") if path.is_file() and ".git" not in path.relative_to(folder).parts}
        check(cloned == snapshot, "Bundle source differs from readable snapshot")
    ticket_map = read_json(REFERENCE / "ticket-map.json")
    known = {item["sha"] for item in commits}
    for ticket, detail in ticket_map["tickets"].items():
        check(set(detail["commits"]) <= known, f"Unknown commit on {ticket}")
        if detail["status"] == "planned":
            check(not detail["commits"], f"Planned ticket has implementation commits {ticket}")
    for name in ("risk-profiling", "unrelated-trading"):
        scope = read_json(REFERENCE / "scopes" / f"{name}.json")
        check(scope["schema_version"] == 1 and set(scope["tickets"]).isdisjoint(scope["excluded_tickets"]), f"Invalid scope {name}")
    return len(commits), head, tree


def main():
    manifest = read_json(REFERENCE / "manifest.json")
    check(manifest["schema_version"] == 1, "Unknown fixture manifest")
    check(len(list(FULL.glob("*.md"))) == 3 and len(list(QUICK.glob("*.md"))) == 1, "Wrong source-page count")
    pages = manifest["pages"]
    for page in pages:
        count = len((ROOT / page["markdown_path"]).read_text(encoding="utf-8"))
        check(count == page["characters"], f"Character count mismatch {page['slug']}")
        minimum, maximum = (3000, 6000) if page["source_id"].startswith("investment-platform/quick") else (70000, 90000)
        check(minimum <= count <= maximum, f"Page outside size band {page['slug']}: {count}")
        if minimum == 70000:
            check(50 <= page["records"] <= 70, f"Wrong substantive record count {page['slug']}")
    for relative, expected in manifest["file_sha256"].items():
        check(sha(ROOT / relative) == expected, f"Fixture file hash mismatch {relative}")
    full_map = validate_page_map(REFERENCE / "source-page-map-full.json", 3)
    quick_map = validate_page_map(REFERENCE / "source-page-map-quick.json", 1)
    assets, unique = validate_assets()
    cases, facts = validate_references(full_map, quick_map)
    commits, head, tree = validate_history()
    print(f"Validated 3 full pages and 1 quick page, {assets} decoded JPEG files ({unique} distinct screens), {cases} citation cases, {facts} facts, {commits} commits")
    print(f"HEAD {head}; tree {tree}")


if __name__ == "__main__":
    main()
