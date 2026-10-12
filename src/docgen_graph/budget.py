import json
import sqlite3
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path
from uuid import uuid4


@dataclass(frozen=True)
class Pricing:
    model: str
    input_usd_per_million: float
    output_usd_per_million: float
    usd_pln: float
    verified_on: date
    valid_until: date
    exchange_date: date
    pricing_source: str
    exchange_source: str

    @classmethod
    def load(cls, path: Path) -> "Pricing":
        raw = json.loads(path.read_text(encoding="utf-8"))
        for key in ("verified_on", "valid_until", "exchange_date"):
            raw[key] = date.fromisoformat(raw[key])
        pricing = cls(**raw)
        today = date.today()
        if (
            pricing.model != "gemini-3.8-flash"
            or not pricing.verified_on <= today <= pricing.valid_until
        ):
            raise ValueError("Current gemini-3.8-flash pricing is required")
        if not today - timedelta(days=7) <= pricing.exchange_date <= today:
            raise ValueError("A recent USD/PLN rate is required")
        if min(pricing.input_usd_per_million, pricing.output_usd_per_million, pricing.usd_pln) <= 0:
            raise ValueError("Pricing rates must be positive")
        return pricing

    def cost(self, input_tokens: int, output_tokens: int) -> float:
        return (
            (
                input_tokens * self.input_usd_per_million
                + output_tokens * self.output_usd_per_million
            )
            * self.usd_pln
            / 1_000_000
        )


class BudgetLedger:
    def __init__(self, path: Path, limit: float | None = None):
        self.path = path.resolve()
        self.limit = limit
        if not self.path.is_file():
            raise ValueError(f"Shared budget ledger is missing: {self.path}")
        with self.connect() as connection:
            columns = {row[1] for row in connection.execute("PRAGMA table_info(charges)")}
        if columns != {
            "id",
            "run_id",
            "stage",
            "time",
            "reserved",
            "charged",
            "status",
            "usage",
            "pricing",
        }:
            raise ValueError("Shared budget ledger schema is incompatible")

    def connect(self):
        return sqlite3.connect(self.path, timeout=30)

    def summary(self) -> dict:
        with self.connect() as connection:
            charged, reserved = connection.execute(
                "SELECT COALESCE(SUM(charged),0), "
                "COALESCE(SUM(CASE WHEN status='reserved' THEN reserved ELSE 0 END),0) "
                "FROM charges"
            ).fetchone()
        return {
            "limit_pln": self.limit,
            "charged_pln": charged,
            "reserved_pln": reserved,
            "remaining_pln": self.limit - charged - reserved if self.limit is not None else None,
        }

    def reserve(self, run_id: str, stage: str, amount: float, pricing: Pricing) -> str:
        if amount <= 0:
            raise ValueError("Reservation must be positive")
        identifier = str(uuid4())
        with self.connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            used = connection.execute(
                "SELECT COALESCE(SUM(charged + CASE WHEN status='reserved' "
                "THEN reserved ELSE 0 END),0) FROM charges"
            ).fetchone()[0]
            if self.limit is not None and used + amount > self.limit:
                raise ValueError(f"Budget exhausted; remaining PLN {self.limit - used:.2f}")
            connection.execute(
                "INSERT INTO charges VALUES (?,?,?,?,?,0,'reserved','{}',?)",
                (
                    identifier,
                    run_id,
                    stage,
                    date.today().isoformat(),
                    amount,
                    json.dumps(pricing.__dict__, default=str),
                ),
            )
        return identifier

    def settle(self, identifier: str, actual: float | None, usage: dict) -> None:
        with self.connect() as connection:
            connection.execute(
                "UPDATE charges SET charged=COALESCE(?,reserved), status=?, usage=? "
                "WHERE id=? AND status='reserved'",
                (
                    actual,
                    "settled" if actual is not None else "uncertain",
                    json.dumps(usage),
                    identifier,
                ),
            )
