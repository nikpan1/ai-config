import sqlite3
from datetime import date, timedelta
from pathlib import Path
from uuid import uuid4

from pydantic import Field

from docgen.contracts import Record
from docgen.storage import encode, now, read_json


class BudgetExceeded(RuntimeError):
    pass


class Pricing(Record):
    model: str
    input_usd_per_million: float = Field(gt=0)
    output_usd_per_million: float = Field(gt=0)
    usd_pln: float = Field(gt=0)
    verified_on: date
    valid_until: date
    exchange_date: date
    pricing_source: str
    exchange_source: str

    def validate_current(self):
        today = date.today()
        if self.model != "gemini-3.8-flash":
            raise ValueError("Pricing must refer to gemini-3.8-flash")
        if not self.verified_on <= today <= self.valid_until:
            raise ValueError(
                "Pricing is missing or expired; verify official pricing before live calls"
            )
        if not today - timedelta(days=7) <= self.exchange_date <= today:
            raise ValueError("USD/PLN exchange rate must be verified within the last seven days")

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
    def __init__(self, path: Path, limit=200.0):
        path.parent.mkdir(parents=True, exist_ok=True)
        self.path = path
        self.limit = min(limit, 200.0)
        with self.connect() as connection:
            connection.execute(
                "CREATE TABLE IF NOT EXISTS charges ("
                "id TEXT PRIMARY KEY, run_id TEXT, stage TEXT, time TEXT, "
                "reserved REAL, charged REAL, status TEXT, usage TEXT, pricing TEXT)"
            )

    def connect(self):
        return sqlite3.connect(self.path, timeout=30)

    def summary(self) -> dict:
        with self.connect() as connection:
            charged, pending = connection.execute(
                "SELECT COALESCE(SUM(charged),0), "
                "COALESCE(SUM(CASE WHEN status='reserved' THEN reserved ELSE 0 END),0) FROM charges"
            ).fetchone()
        return {
            "limit_pln": self.limit,
            "charged_pln": charged,
            "reserved_pln": pending,
            "remaining_pln": self.limit - charged - pending,
        }

    def reserve(self, run_id, stage, amount, pricing: Pricing) -> str:
        pricing.validate_current()
        identifier = str(uuid4())
        with self.connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            used = connection.execute(
                "SELECT COALESCE(SUM(charged + CASE WHEN status='reserved' "
                "THEN reserved ELSE 0 END),0) FROM charges"
            ).fetchone()[0]
            if used + amount > self.limit:
                raise BudgetExceeded(
                    f"Request requires {amount:.2f} PLN; remaining {self.limit - used:.2f} PLN"
                )
            connection.execute(
                "INSERT INTO charges VALUES (?,?,?,?,?,0,'reserved','{}',?)",
                (identifier, run_id, stage, now(), amount, encode(pricing)),
            )
        return identifier

    def settle(self, identifier: str, actual: float | None, usage: dict):
        with self.connect() as connection:
            connection.execute(
                "UPDATE charges SET charged=COALESCE(?,reserved), "
                "status=?, usage=? WHERE id=? AND status='reserved'",
                (
                    actual,
                    "settled" if actual is not None else "uncertain",
                    encode(usage),
                    identifier,
                ),
            )


def load_pricing(path: Path) -> Pricing:
    if not path.exists():
        raise ValueError("Pricing file is required before live calls")
    pricing = Pricing.model_validate(read_json(path))
    pricing.validate_current()
    return pricing
