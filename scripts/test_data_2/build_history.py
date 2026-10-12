import hashlib
import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

from records.content import REVISION, STORIES


ROOT = Path(__file__).resolve().parents[2]
SOURCE = Path(__file__).resolve().parent / "records" / "app"
SNAPSHOT = ROOT / "data" / "investment_platform"
HISTORY = ROOT / "data" / "investment_platform_history"
REFERENCE = ROOT / "data" / "test_data_2_reference"
TEMP_ROOT = ROOT / ".docgen" / "fixtures"

STAGES = [
    ("TICKET-1000", "establish synthetic platform and local configuration", [".gitattributes", ".env.example", "compose.yaml", "backend/pom.xml", "backend/mvnw", "backend/mvnw.cmd", "backend/.mvn/wrapper/maven-wrapper.properties", "backend/src/main/resources/application.yaml", "backend/src/main/java/example/fixture/InvestmentApplication.java", "README.md"]),
    ("TICKET-1001", "define profile and dictionary persistence", ["database/postgres/001_schema.sql"]),
    ("TICKET-1002", "seed synthetic investor and Q3 dictionaries", ["database/postgres/002_seed.sql"]),
    ("TICKET-2001", "define draft and assessment contracts", ["backend/src/main/java/example/fixture/ProfileDtos.java"]),
    ("TICKET-3001", "add quote and reservation provider adapter", ["backend/src/main/java/example/fixture/TradingController.java"]),
    ("TICKET-2002", "persist versioned drafts and accepted profile history", ["backend/src/main/java/example/fixture/ProfileRepository.java"]),
    ("TICKET-2003", "add versioned RiskSignal client", ["backend/src/main/java/example/fixture/RiskSignalClient.java"]),
    ("TICKET-2004", "record questionnaire and provider audits in MongoDB", ["backend/src/main/java/example/fixture/MongoAuditRepository.java"]),
    ("TICKET-2005", "validate, submit and recover profile assessments", ["backend/src/main/java/example/fixture/RiskProfileService.java"]),
    ("TICKET-3002", "add deterministic market and provider stubs", ["mocks/rules-rs-2026-09.json", "mocks/stub.py"]),
    ("TICKET-2006", "expose profile draft, submission and history endpoints", ["backend/src/main/java/example/fixture/ProfileController.java"]),
    ("TICKET-1003", "index immutable Mongo answer and provider evidence", ["database/mongo/init.js"]),
    ("TICKET-2007", "test idempotency, incomplete response and stale version", ["backend/src/test/java/example/fixture/RiskProfileServiceTest.java"]),
    ("TICKET-2008", "scaffold Angular Q3 questionnaire client", ["frontend/package.json", "frontend/package-lock.json", "frontend/angular.json", "frontend/proxy.conf.json", "frontend/tsconfig.json", "frontend/tsconfig.spec.json", "frontend/src/index.html", "frontend/src/styles.css", "frontend/src/main.ts", "frontend/src/profile-api.ts"]),
    ("TICKET-3003", "persist custody reservation and order state", ["database/postgres/003_orders.sql", "backend/src/main/java/example/fixture/OrderRepository.java", "backend/src/main/java/example/fixture/TradingController.java"]),
    ("TICKET-2009", "build questionnaire, result and history views", ["frontend/src/app.component.ts", "frontend/src/app.component.html"]),
    ("TICKET-3004", "add quote browsing to shared Angular shell", ["frontend/src/trading-api.ts", "frontend/src/app.component.ts", "frontend/src/app.component.html"]),
    ("TICKET-2007", "verify Angular submission retry contract", ["frontend/src/profile-api.spec.ts"]),
    ("TICKET-2010", "test accepted result display without trading calls", ["frontend/src/app.component.spec.ts"]),
    ("TICKET-2019", "reject legacy free-text loss tolerance at boundary", ["backend/src/main/java/example/fixture/ProfileRepository.java"]),
    ("TICKET-2011", "document authoritative stores and history policy", ["README.md"]),
]


def sha(content):
    return hashlib.sha256(content).hexdigest()


def run(*args, cwd=None, env=None):
    result = subprocess.run(args, cwd=cwd, env=env, text=True, encoding="utf-8", stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
    if result.returncode:
        raise RuntimeError(f"{' '.join(str(item) for item in args)} failed: {result.stderr}")
    return result.stdout.strip()


def source_files():
    files = {}
    for path in SOURCE.rglob("*"):
        if path.is_file() and not ({"__pycache__", "node_modules", "target", "dist"} & set(path.parts)) and path.suffix not in {".pyc", ".class"}:
            files[path.relative_to(SOURCE).as_posix()] = path.read_bytes()
    return files


def staged_content(name, ticket, content):
    plain = content.decode("utf-8")
    if name == "README.md" and ticket == "TICKET-1000":
        return b"# Northstar Investment synthetic platform\n\nLocal fictional investment-platform fixture. Start databases and stubs with `docker compose up`.\n"
    if name.endswith("ProfileRepository.java") and ticket == "TICKET-2002":
        return plain.replace("    public boolean allowed(String dictionary, String code) {\n", "    public boolean allowed(String dictionary, String code) {\n        if (\"loss-tolerance\".equals(dictionary) && \"5.1\".equals(code)) return true;\n").encode("utf-8")
    if name.endswith("TradingController.java") and ticket == "TICKET-3001":
        plain = plain.replace("    private final OrderRepository orders;\n", "")
        plain = plain.replace(", OrderRepository orders)", ")")
        plain = plain.replace("        this.orders = orders;\n", "")
        start = plain.index("    @PostMapping(\"/orders/{orderRef}/reserve\")")
        plain = plain[:start] + "    @PostMapping(\"/reservations\")\n    public Map reserve(@RequestBody Map<String, Object> request) {\n        return custody.post().uri(\"/reservations\").body(request).retrieve().body(Map.class);\n    }\n}\n"
        return plain.encode("utf-8")
    if name.endswith("app.component.ts") and ticket == "TICKET-2009":
        plain = plain.replace("import { Quote, TradingApi } from './trading-api';\n", "")
        plain = plain.replace("  private readonly trading = inject(TradingApi);\n", "")
        plain = plain.replace("  quote?: Quote;\n", "")
        start = plain.index("  loadQuote(): void {")
        plain = plain[:start] + "}\n"
        return plain.encode("utf-8")
    if name.endswith("app.component.html") and ticket == "TICKET-2009":
        plain = plain.replace('<section *ngIf="view===\'quotes\'"><h2>Quote context</h2><p>MarketPulse data is unrelated to investor risk profiling.</p><label>Instrument<input [(ngModel)]="quoteInstrument"></label><button (click)="loadQuote()">Load quote</button><p *ngIf="quote">{{ quote.bid }} / {{ quote.ask }} {{ quote.quoteCurrency }} · {{ quote.session }} · {{ quote.asOf }}</p></section>', '<section *ngIf="view===\'quotes\'"><h2>Quote context</h2><p>MarketPulse browsing is planned for the next trading story.</p></section>')
        return plain.encode("utf-8")
    return content


def inventory(root):
    return {path.relative_to(root).as_posix(): sha(path.read_bytes()) for path in root.rglob("*") if path.is_file() and ".git" not in path.relative_to(root).parts}


def build_repository(folder, files):
    run("git", "init", "--initial-branch=main", str(folder))
    run("git", "config", "core.autocrlf", "false", cwd=folder)
    run("git", "config", "commit.gpgsign", "false", cwd=folder)
    run("git", "config", "user.name", "Fixture Builder", cwd=folder)
    run("git", "config", "user.email", "fixture-builder@example.invalid", cwd=folder)
    commits = []
    for index, (ticket, subject, paths) in enumerate(STAGES):
        for relative in paths:
            if relative not in files:
                raise RuntimeError(f"Missing application source: {relative}")
            destination = folder / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(staged_content(relative, ticket, files[relative]))
        run("git", "add", "--", *paths, cwd=folder)
        if not run("git", "diff", "--cached", "--name-only", cwd=folder):
            raise RuntimeError(f"Empty stage: {ticket} {subject}")
        env = os.environ.copy()
        timestamp = f"2026-09-{index + 1:02d}T09:00:00+00:00"
        env.update({"GIT_AUTHOR_DATE": timestamp, "GIT_COMMITTER_DATE": timestamp, "TZ": "UTC"})
        run("git", "commit", "-m", f"{ticket} {subject}", cwd=folder, env=env)
        commit = run("git", "rev-parse", "HEAD", cwd=folder)
        changed = run("git", "diff-tree", "--no-commit-id", "--name-only", "-r", "HEAD", cwd=folder).splitlines()
        if index == 0:
            changed = run("git", "ls-tree", "-r", "--name-only", "HEAD", cwd=folder).splitlines()
        commits.append({"ticket": ticket, "subject": f"{ticket} {subject}", "sha": commit, "changed_paths": changed})
    actual = inventory(folder)
    expected = {name: sha(content) for name, content in files.items()}
    if actual != expected:
        raise RuntimeError(f"Final history tree differs from application source: {set(actual.items()) ^ set(expected.items())}")
    return commits


def write_snapshot(files):
    if SNAPSHOT.exists():
        current = inventory(SNAPSHOT)
        previous_path = HISTORY / "manifest.json"
        previous = json.loads(previous_path.read_text(encoding="utf-8"))["file_sha256"] if previous_path.exists() else {}
        if current != previous:
            raise RuntimeError("Application snapshot contains unknown or edited files")
    for relative, content in files.items():
        destination = SNAPSHOT / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(content)


def make_ticket_map(commits):
    by_ticket = {}
    for commit in commits:
        by_ticket.setdefault(commit["ticket"], []).append(commit)
    tickets = {}
    for number, title, _, _, _, _ in STORIES:
        ticket = f"TICKET-{number}"
        direct = by_ticket.get(ticket, [])
        implemented = number not in {"2018", "2020"}
        mapped = direct or (by_ticket.get("TICKET-2005", []) if implemented else [])
        tickets[ticket] = {"scope": "risk-profiling", "status": "partial" if number == "2013" else "implemented" if implemented else "planned", "prerequisites": ["TICKET-1001", "TICKET-1002", "TICKET-2000"], "commits": [item["sha"] for item in mapped], "changed_paths": sorted({path for item in mapped for path in item["changed_paths"]}), "tests": ["backend/src/test/java/example/fixture/RiskProfileServiceTest.java"] if implemented else [], "source_sections": [f"STORY-{number}-1", f"STORY-{number}-2", f"STORY-{number}-3"], "expected_behavior": title}
    tickets["TICKET-2000"] = {"scope": "risk-profiling", "status": "epic", "prerequisites": ["TICKET-1001", "TICKET-1002"], "commits": sorted({sha for ticket, item in tickets.items() if ticket != "TICKET-2000" for sha in item["commits"]}), "changed_paths": [], "tests": ["backend/src/test/java/example/fixture/RiskProfileServiceTest.java", "frontend/src/profile-api.spec.ts"], "source_sections": ["TICKET-2000"], "expected_behavior": "Q3 risk-profile journey"}
    for ticket, records in by_ticket.items():
        if ticket in tickets:
            continue
        tickets[ticket] = {"scope": "trading" if ticket.startswith("TICKET-3") else "shared", "status": "implemented", "prerequisites": [], "commits": [record["sha"] for record in records], "changed_paths": sorted({path for record in records for path in record["changed_paths"]}), "tests": [], "source_sections": [], "expected_behavior": records[0]["subject"].split(" ", 1)[1]}
    for number in range(2021, 2025):
        ticket = f"TICKET-{number}"
        tickets[ticket] = {"scope": "risk-profiling", "status": "planned", "prerequisites": ["TICKET-2000"], "commits": [], "changed_paths": [], "tests": [], "source_sections": [], "expected_behavior": "Future follow-up; no fixture implementation"}
    write_json(REFERENCE / "ticket-map.json", {"schema_version": 1, "fixture_revision": REVISION, "tickets": tickets})
    risk = ["TICKET-2000"] + [ticket for ticket in tickets if ticket.startswith("TICKET-2") and tickets[ticket]["status"] in {"implemented", "partial"}]
    write_json(REFERENCE / "scopes" / "risk-profiling.json", {"schema_version": 1, "fixture_revision": REVISION, "feature": "risk-profiling", "tickets": risk, "dependency_tickets": ["TICKET-1000", "TICKET-1001", "TICKET-1002", "TICKET-1003"], "excluded_tickets": ["TICKET-3001", "TICKET-3002", "TICKET-3003", "TICKET-3004"]})
    write_json(REFERENCE / "scopes" / "unrelated-trading.json", {"schema_version": 1, "fixture_revision": REVISION, "feature": "trading", "tickets": ["TICKET-3001", "TICKET-3002", "TICKET-3003", "TICKET-3004"], "dependency_tickets": ["TICKET-1000", "TICKET-1001"], "excluded_tickets": risk})


def write_json(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes((json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8"))


def main():
    files = source_files()
    staged = {relative for _, _, paths in STAGES for relative in paths}
    if set(files) != staged:
        raise RuntimeError(f"Unstaged application files: {set(files) - staged}; missing source: {staged - set(files)}")
    TEMP_ROOT.mkdir(parents=True, exist_ok=True)
    HISTORY.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="history-", dir=TEMP_ROOT) as work:
        build = Path(work) / "build"
        clone = Path(work) / "clone"
        commits = build_repository(build, files)
        head = run("git", "rev-parse", "HEAD", cwd=build)
        tree = run("git", "rev-parse", "HEAD^{tree}", cwd=build)
        bundle = HISTORY / "investment-platform.bundle"
        if bundle.exists() and (HISTORY / "manifest.json").exists():
            previous = json.loads((HISTORY / "manifest.json").read_text(encoding="utf-8"))
            if sha(bundle.read_bytes()) != previous["bundle_sha256"]:
                raise RuntimeError("Existing bundle was edited outside the builder")
        run("git", "bundle", "create", str(bundle), "--all", cwd=build)
        run("git", "bundle", "verify", str(bundle), cwd=build)
        run("git", "clone", "--quiet", str(bundle), str(clone))
        if run("git", "rev-parse", "HEAD", cwd=clone) != head or inventory(clone) != {name: sha(content) for name, content in files.items()}:
            raise RuntimeError("Bundle clone does not match final source")
        write_snapshot(files)
        manifest = {"schema_version": 1, "fixture_revision": REVISION, "ref": "refs/heads/main", "head": head, "tree": tree, "bundle_path": "data/investment_platform_history/investment-platform.bundle", "bundle_sha256": sha(bundle.read_bytes()), "file_sha256": {name: sha(content) for name, content in sorted(files.items())}, "packaging_exclusions": [], "commits": commits, "commit_count": len(commits)}
        write_json(HISTORY / "manifest.json", manifest)
        make_ticket_map(commits)
        fixture_manifest_path = REFERENCE / "manifest.json"
        if fixture_manifest_path.exists():
            fixture_manifest = json.loads(fixture_manifest_path.read_text(encoding="utf-8"))
            fixture_manifest["history"] = {"head": head, "tree": tree, "ref": "refs/heads/main", "bundle_path": "data/investment_platform_history/investment-platform.bundle", "bundle_sha256": sha(bundle.read_bytes()), "commit_count": len(commits)}
            fixture_manifest["file_sha256"]["data/test_data_2_reference/ticket-map.json"] = sha((REFERENCE / "ticket-map.json").read_bytes())
            for name in ("risk-profiling", "unrelated-trading"):
                relative = f"data/test_data_2_reference/scopes/{name}.json"
                fixture_manifest["file_sha256"][relative] = sha((ROOT / relative).read_bytes())
            write_json(fixture_manifest_path, fixture_manifest)
        print(f"{len(commits)} commits; HEAD {head}; tree {tree}")


if __name__ == "__main__":
    main()
