import json
import sqlite3
from collections import defaultdict
from pathlib import Path

database = Path(__file__).resolve().parents[1] / ".docgen" / "budget.sqlite"
connection = sqlite3.connect(database)
rows = connection.execute(
    "SELECT run_id, stage, reserved, charged, status, usage, pricing "
    "FROM charges WHERE run_id LIKE 'furniture-%' ORDER BY time, id"
).fetchall()
totals = defaultdict(
    lambda: {
        "calls": 0,
        "settled_calls": 0,
        "uncertain_calls": 0,
        "reserved_calls": 0,
        "input_tokens": 0,
        "output_tokens": 0,
        "measured_pln": 0.0,
        "charged_pln": 0.0,
        "uncertain_charged_pln": 0.0,
        "reserved_pln": 0.0,
    }
)
for run_id, stage, reserved, charged, status, usage_json, pricing_json in rows:
    usage = json.loads(usage_json)
    pricing = json.loads(pricing_json)
    token_usage = usage.get("usage", usage)
    if not isinstance(token_usage, dict):
        token_usage = {}
    input_tokens = token_usage.get("input_tokens", token_usage.get("prompt_token_count", 0))
    output_tokens = token_usage.get("output_tokens", token_usage.get("candidates_token_count", 0))
    input_tokens = input_tokens or 0
    output_tokens = output_tokens or 0
    measured = (
        input_tokens * pricing["input_usd_per_million"]
        + output_tokens * pricing["output_usd_per_million"]
    ) * pricing["usd_pln"] / 1_000_000
    for key in (run_id, "old" if run_id.startswith("furniture-old-") else "new", "all"):
        item = totals[key]
        item["calls"] += 1
        item["settled_calls"] += status == "settled"
        item["uncertain_calls"] += status == "uncertain"
        item["reserved_calls"] += status == "reserved"
        item["input_tokens"] += input_tokens
        item["output_tokens"] += output_tokens
        item["measured_pln"] += measured
        item["charged_pln"] += charged
        item["uncertain_charged_pln"] += charged if status == "uncertain" else 0
        item["reserved_pln"] += reserved if status == "reserved" else 0

for item in totals.values():
    for key in ("measured_pln", "charged_pln", "uncertain_charged_pln", "reserved_pln"):
        item[key] = round(item[key], 4)
print(json.dumps(dict(totals), indent=2, ensure_ascii=False))
