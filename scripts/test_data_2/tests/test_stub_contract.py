import json
import socket
import subprocess
import sys
import time
import unittest
import urllib.error
import urllib.request
from pathlib import Path


STUB = Path(__file__).resolve().parents[1] / "records" / "app" / "mocks" / "stub.py"


def free_port():
    with socket.socket() as connection:
        connection.bind(("127.0.0.1", 0))
        return connection.getsockname()[1]


def get(port, path):
    with urllib.request.urlopen(f"http://127.0.0.1:{port}{path}", timeout=2) as response:
        return json.loads(response.read())


def post(port, path, payload):
    outgoing = urllib.request.Request(f"http://127.0.0.1:{port}{path}", data=json.dumps(payload).encode("utf-8"), method="POST", headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(outgoing, timeout=2) as response:
            return response.status, json.loads(response.read())
    except urllib.error.HTTPError as error:
        return error.code, json.loads(error.read())


class StubContractTest(unittest.TestCase):
    def setUp(self):
        self.processes = []
        self.ports = {}
        for service in ("RiskSignal", "MarketPulse", "CustodyBridge"):
            port = free_port()
            process = subprocess.Popen([sys.executable, str(STUB), service, str(port)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            self.processes.append(process)
            self.ports[service] = port
            for _ in range(40):
                try:
                    get(port, "/health")
                    break
                except (OSError, urllib.error.URLError):
                    time.sleep(0.05)
            else:
                self.fail(f"{service} stub did not start")

    def tearDown(self):
        for process in self.processes:
            process.terminate()
            process.wait(timeout=5)

    def test_risk_contract_and_unrelated_provider_isolation(self):
        request = {"investorRef": "INV-100", "questionnaireVersion": "Q3", "rulesVersion": "RS-2026-09", "experience": "BEGINNER", "horizon": "H3", "lossTolerance": "L5", "liquidityNeed": "FLEXIBLE", "consentRevision": "CP-3", "idempotencyKey": "key-test-01", "correlationId": "corr-test-01"}
        risk = self.ports["RiskSignal"]
        first_status, first = post(risk, "/assessments", request)
        repeated_status, repeated = post(risk, "/assessments", request)
        conflict_status, _ = post(risk, "/assessments", request | {"horizon": "H7"})
        self.assertEqual((first_status, repeated_status, conflict_status), (200, 200, 409))
        self.assertEqual(first, repeated)
        self.assertEqual(first["proposedBand"], "R2")
        self.assertEqual(first["responseRulesVersion"], "RS-2026-09")
        self.assertEqual(len(get(self.ports["MarketPulse"], "/_calls")["calls"]), 0)
        self.assertEqual(len(get(self.ports["CustodyBridge"], "/_calls")["calls"]), 0)


if __name__ == "__main__":
    unittest.main()
