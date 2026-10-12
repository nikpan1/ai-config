import json
import sys
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path


SERVICE = sys.argv[1]
PORT = int(sys.argv[2])
CALLS = []
ASSESSMENTS = {}
MODE = "ok"
RULES = json.loads((Path(__file__).parent / "rules-rs-2026-09.json").read_text(encoding="utf-8"))


class Handler(BaseHTTPRequestHandler):
    def send_json(self, status, payload):
        body = json.dumps(payload, separators=(",", ":")).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path == "/health":
            return self.send_json(200, {"service": SERVICE, "status": "healthy"})
        if self.path == "/_calls":
            return self.send_json(200, {"calls": CALLS})
        if SERVICE == "MarketPulse" and self.path.startswith("/quotes/"):
            CALLS.append({"path": self.path})
            return self.send_json(200, {"instrumentId": self.path.split("/")[-1], "bid": 101.25, "ask": 101.40, "quoteCurrency": "PLN", "session": "OPEN", "instrumentRisk": "MEDIUM", "asOf": "2026-10-01T12:00:00Z"})
        return self.send_json(404, {"error": "NOT_FOUND"})

    def do_POST(self):
        global MODE
        size = int(self.headers.get("Content-Length", "0"))
        payload = json.loads(self.rfile.read(size) or b"{}")
        if self.path == "/_mode" and SERVICE == "RiskSignal":
            if payload.get("mode") not in {"ok", "unavailable"}:
                return self.send_json(400, {"error": "UNKNOWN_MODE"})
            MODE = payload["mode"]
            return self.send_json(200, {"mode": MODE})
        CALLS.append({"path": self.path, "correlationId": payload.get("correlationId")})
        if SERVICE == "RiskSignal" and self.path == "/assessments":
            if MODE == "unavailable":
                return self.send_json(503, {"error": "UNAVAILABLE"})
            if payload.get("rulesVersion") != RULES["version"] or payload.get("questionnaireVersion") != "Q3":
                return self.send_json(409, {"error": "OUTDATED_RULESET"})
            required = ("investorRef", "experience", "horizon", "lossTolerance", "liquidityNeed", "consentRevision", "idempotencyKey", "correlationId")
            if any(not payload.get(field) for field in required):
                return self.send_json(422, {"error": "INCOMPLETE_REQUEST"})
            key = payload["idempotencyKey"]
            previous = ASSESSMENTS.get(key)
            if previous and previous["request"] != payload:
                return self.send_json(409, {"error": "IDEMPOTENCY_CONFLICT"})
            if previous:
                return self.send_json(200, previous["response"])
            band = RULES["base_band"]
            if any(payload.get(key) == value for key, value in RULES["cautious_if"].items()):
                band = "R1"
            elif all(payload.get(key) == value for key, value in RULES["growth_if"].items()):
                band = "R3"
            reasons = [RULES["reasons"].get(payload["horizon"], "HORIZON_OTHER"), RULES["reasons"].get(payload["lossTolerance"], "LOSS_OTHER")]
            response = {"providerAssessmentId": "rs-" + key, "proposedBand": band, "reasonCodes": reasons, "responseRulesVersion": RULES["version"], "evaluatedAt": "2026-10-01T12:00:00Z"}
            ASSESSMENTS[key] = {"request": payload, "response": response}
            return self.send_json(200, response)
        if SERVICE == "CustodyBridge" and self.path == "/reservations":
            if not payload.get("reservationKey") or not payload.get("amount"):
                return self.send_json(422, {"error": "INVALID_RESERVATION"})
            return self.send_json(200, {"reservationId": "cb-" + str(payload["reservationKey"]), "reservationStatus": "RESERVED"})
        return self.send_json(404, {"error": "NOT_FOUND"})


HTTPServer(("0.0.0.0", PORT), Handler).serve_forever()
