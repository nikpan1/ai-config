import json
import urllib.error
import urllib.request
import uuid


def request(method, url, payload=None, expected=200):
    body = json.dumps(payload).encode("utf-8") if payload is not None else None
    outgoing = urllib.request.Request(url, data=body, method=method, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(outgoing, timeout=8) as response:
            status = response.status
            content = response.read()
    except urllib.error.HTTPError as error:
        status = error.code
        content = error.read()
    if status != expected:
        raise AssertionError(f"{method} {url}: expected {expected}, received {status}: {content.decode('utf-8')}")
    return json.loads(content) if content and content.startswith((b"{", b"[")) else content.decode("utf-8")


def calls(port):
    return len(request("GET", f"http://127.0.0.1:{port}/_calls")["calls"])


def complete_draft():
    backend = "http://127.0.0.1:8080/api/profile"
    draft = request("POST", f"{backend}/drafts", {"investorRef": "INV-100"})
    updated = request("PATCH", f"{backend}/drafts/{draft['draftId']}", {"experience": "BEGINNER", "horizon": "H3", "lossTolerance": "L5", "liquidityNeed": "FLEXIBLE", "processingConsent": True, "revision": draft["revision"]})
    return updated["draftId"]


def main():
    backend = "http://127.0.0.1:8080/api/profile"
    before = {name: calls(port) for name, port in (("risk", 8091), ("market", 8092), ("custody", 8093))}
    first = complete_draft()
    key = str(uuid.uuid4())
    result = request("POST", f"{backend}/drafts/{first}/submit", {"idempotencyKey": key})
    repeat = request("POST", f"{backend}/drafts/{first}/submit", {"idempotencyKey": key})
    if result != repeat or result["band"] not in {"R1", "R2", "R3", "R4"} or not result["providerAssessmentId"]:
        raise AssertionError("Accepted result or duplicate behavior is invalid")
    history = request("GET", f"{backend}/investors/INV-100/history")
    if history[0]["assessmentId"] != result["assessmentId"]:
        raise AssertionError("Persisted history does not contain accepted result")
    request("POST", "http://127.0.0.1:8091/_mode", {"mode": "unavailable"})
    try:
        second = complete_draft()
        request("POST", f"{backend}/drafts/{second}/submit", {"idempotencyKey": str(uuid.uuid4())}, expected=503)
    finally:
        request("POST", "http://127.0.0.1:8091/_mode", {"mode": "ok"})
    after_history = request("GET", f"{backend}/investors/INV-100/history")
    if after_history[0]["assessmentId"] != result["assessmentId"]:
        raise AssertionError("Failed reassessment replaced the previous active result")
    after = {name: calls(port) for name, port in (("risk", 8091), ("market", 8092), ("custody", 8093))}
    if after["market"] != before["market"] or after["custody"] != before["custody"]:
        raise AssertionError("Risk workflow invoked an unrelated provider")
    if after["risk"] - before["risk"] != 3:
        raise AssertionError("Expected one accepted assessment call and two failed attempts")
    print("Core, idempotency, provider failure, persistence and provider isolation passed")


if __name__ == "__main__":
    main()
