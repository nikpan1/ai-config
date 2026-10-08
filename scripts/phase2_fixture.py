import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from docgen.ingestion import estimate_tokens
from docgen.storage import atomic_write, write_json


def make_fixture(root=Path(".docgen/phase2-medium-source")):
    root.mkdir(parents=True, exist_ok=True)
    header = (
        "# Record operations specification\n\n"
        "Source status: approved requirements for evaluation, not evidence of implementation. "
        "This is an autonomously authored synthetic fixture, not user-reviewed legacy knowledge. "
        "Archive operations preserve records for later retrieval. Delivery operations distribute "
        "a requested record to an authorized recipient. These are independently useful outcomes; "
        "delivery can request a live record or an archived record. Profile identifiers define "
        "mutually distinct operational scopes; rules from one profile never apply to another. "
        "ArchiveService and DeliveryService are stable service identifiers, each with one identity "
        "across this entire specification. Both are in version 1. Their mentions in separate "
        "profiles refer to those same services, while profile-specific record types "
        "remain distinct.\n\n"
        "## Shared requirements\n\n"
        "Every accepted archive or delivery action must write an audit entry containing the "
        "profile ID, request ID, actor ID, outcome and timestamp in UTC. Both functional areas "
        "use this single audit requirement. Audit entries must omit record payloads and recipient "
        "contact details. If the audit store is unavailable, the action remains pending and "
        "must not be reported as successful. The source does not specify audit retention or "
        "administrator bypass permissions; those attributes are explicitly unknown.\n\n"
    )
    streams = [header, header]
    reference = []
    for number in range(1, 25):
        for area in ("Archive", "Delivery"):
            profile = f"{area[0]}P-{number:03}"
            destination = (number + (area == "Delivery")) % 2
            retention = 30 + number
            attempts = 2 + number % 3
            hour = number % 24
            if area == "Archive":
                paragraph = (
                    f"### Archive profile {profile}\n\n"
                    f"Scope: ArchiveService version 1, profile {profile}. This profile governs "
                    f"retention and recovery of a record after {retention} complete days without "
                    f"an accepted update. A profile operator must first submit an archive request "
                    f"containing the record ID, profile ID and original request key. "
                    f"An independent "
                    f"profile reviewer must approve that request before it is eligible for the "
                    f"daily archive pass at {hour:02}:00 UTC. The same person cannot submit and "
                    f"approve one request. A legal hold prevents archiving even when approval and "
                    f"the age threshold are satisfied. When any prerequisite is missing, the "
                    f"record remains Active and the existing revision must remain unchanged. "
                    f"The daily pass changes an eligible record from Active to Archived only "
                    f"after the archive store confirms a durable write and the shared audit "
                    f"requirement succeeds. The source specifies no intermediate archive state.\n\n"
                    f"For {profile}, a failed durable write requires recovery with the original "
                    f"request key, never a newly generated key. Recovery is limited to {attempts} "
                    f"automatic attempts, separated by 15 minutes. Every failed attempt preserves "
                    f"the previously readable revision. After the final failed attempt, the "
                    f"request is marked RecoveryRequired and must be examined by a profile "
                    f"operator; the record itself remains Active. Manual recovery is permitted "
                    f"only after the store is available and the reviewer approval remains valid. "
                    f"The legal hold must be checked again before manual recovery writes anything. "
                    f"The service returns the preserved revision ID with each failed attempt so "
                    f"the operator can inspect what remains readable. This recovery outcome is "
                    f"part of the archive journey, not an independent functional area. No restore "
                    f"from Archived to Active is specified for this profile. The absence of a "
                    f"restore requirement must remain an unknown; it does not establish that "
                    f"restoration is impossible or that an administrator can perform it.\n\n"
                    f"The {profile} archive receipt contains the record ID, archived revision, "
                    f"profile ID and confirmed archive timestamp. DeliveryService may use the "
                    f"receipt's revision ID to request that exact archived record. A receipt "
                    f"does not grant delivery permission. Archive operators may read status and "
                    f"request manual recovery only within {profile}; this permission does not "
                    f"grant approval authority or access to another profile. The profile's "
                    f"retention threshold is {retention} days and its scheduling time is "
                    f"{hour:02}:00 UTC; those values are intentionally profile-specific and must "
                    f"not be generalized across the archive service.\n\n"
                )
                expected = {
                    "retention_days": retention,
                    "utc_hour": hour,
                    "retry_limit": attempts,
                    "conditions": ["approval", "legal hold", "unchanged revision"],
                    "flow": "archive and recovery",
                }
            else:
                paragraph = (
                    f"### Delivery profile {profile}\n\n"
                    f"Scope: DeliveryService version 1, profile {profile}. A delivery operator "
                    f"may request dispatch of a live or archived record only to a recipient "
                    f"authorized for that exact profile. The request must contain the record ID, "
                    f"revision ID, recipient ID and a stable dispatch key. An archive receipt "
                    f"can identify the requested revision but is not proof of "
                    f"recipient permission. "
                    f"The service must check recipient authorization and verify that the requested "
                    f"revision is readable before creating a Prepared dispatch. If either check "
                    f"fails, the request is Rejected and no dispatch is created. A recipient "
                    f"suspension blocks dispatch even if an earlier authorization check passed. "
                    f"The source specifies no automatic privilege to override suspension.\n\n"
                    f"For {profile}, the dispatch window begins daily at {hour:02}:30 UTC. Within "
                    f"that window the service rechecks suspension, submits the prepared payload "
                    f"to the delivery gateway, and waits for the gateway receipt. The Prepared "
                    f"dispatch becomes Sent only after that receipt and the shared audit "
                    f"requirement both succeed. Gateway acceptance alone does not establish that "
                    f"the recipient has opened or read the record. Reading confirmation is "
                    f"explicitly outside this specification, so the plan must not invent a Read "
                    f"state. The gateway receipt contains the stable dispatch key, gateway "
                    f"reference and accepted timestamp. The delivery operator can inspect the "
                    f"receipt within {profile}, but cannot inspect another profile's "
                    f"recipients.\n\n"
                    f"A gateway timeout in {profile} leaves the dispatch Prepared and records "
                    f"DeliveryUncertain on the request. Recovery must query the gateway by the "
                    f"original dispatch key before considering another submission. If the gateway "
                    f"returns an existing receipt, the service must reuse that receipt and must "
                    f"not send the payload again. Only an explicit NotFound response permits "
                    f"another submission with the same dispatch key. Automatic resubmission is "
                    f"limited to {attempts} attempts, separated by 15 minutes; "
                    f"recipient suspension "
                    f"must be checked again before each one. After that limit the request remains "
                    f"DeliveryUncertain for operator investigation. A timeout is never evidence "
                    f"that the earlier submission was not received. The source does not specify "
                    f"how long a gateway stores idempotency keys, and that limitation must remain "
                    f"visible near the recovery explanation.\n\n"
                    f"Dispatch receipts for {profile} remain available for {retention} days after "
                    f"Sent. This is receipt availability, not an archive retention rule and not "
                    f"a statement that the underlying record is deleted. Delivery operators "
                    f"cannot change archive holds or approve archive requests through the delivery "
                    f"interface. The different archive and delivery states must retain their "
                    f"separate meanings even when a dispatch references an archived record.\n\n"
                )
                expected = {
                    "receipt_days": retention,
                    "utc_hour": hour,
                    "retry_limit": attempts,
                    "conditions": [
                        "recipient authorization",
                        "suspension",
                        "original dispatch key",
                    ],
                    "flow": "delivery and uncertainty recovery",
                }
            streams[destination] += paragraph
            reference.append({"profile": profile, "area": area, "expected": expected})
    paths = []
    for index, text in enumerate(streams):
        path = root / f"interleaved-{index + 1}.md"
        atomic_write(path, text)
        paths.append(path)
    questions = [
        "Which business outcomes distinguish archiving from delivery?",
        "When is AP-001 eligible for its daily archive pass?",
        "What happens when an archive record is on hold?",
        "May the submitter approve the same archive request?",
        "Which revision survives a failed archive write?",
        "Which request key must archive recovery reuse?",
        "Does an archive receipt grant recipient authorization?",
        "What prevents a Prepared dispatch from becoming Sent?",
        "What must happen after a gateway timeout before resubmission?",
        "When does a gateway receipt prevent another delivery?",
        "Can an operator inspect another profile's recipients?",
        "Does receipt availability determine archive record retention?",
        "Which audit failure blocks both functional outcomes?",
        "Which lifecycle transitions and key-retention attributes remain unknown?",
    ]
    summary = {
        "source_paths": [str(p) for p in paths],
        "profiles": reference,
        "estimated_source_tokens": sum(estimate_tokens(t) for t in streams),
        "reader_questions": questions,
        "expected_unit_count": 2,
        "modality": "requirement",
        "manual_review": "not_performed",
        "fixture_origin": "autonomously_authored_synthetic",
        "held_out": False,
    }
    write_json(Path("evaluation/phase2-reference.json"), summary)
    print(
        {"estimated_source_tokens": summary["estimated_source_tokens"], "profiles": len(reference)}
    )


if __name__ == "__main__":
    make_fixture()
