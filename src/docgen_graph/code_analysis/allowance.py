import json
import math
from datetime import date, timedelta

from docgen_graph.budget import BudgetLedger, Pricing


class ProviderAllowance:
    def __init__(self, settings, run_id):
        path = settings.code_provider_allowance_file
        raw = json.loads(path.read_text("utf-8"))
        if (raw.get("provider"), raw.get("model")) != (
            settings.code_analysis_backend,
            settings.code_analysis_model,
        ):
            raise ValueError("Provider allowance must match the selected backend and model")
        if not raw.get("authorization_ref"):
            raise ValueError("Provider allowance requires an authorization reference")
        pricing = raw["pricing"]
        for key in ("verified_on", "valid_until", "exchange_date"):
            pricing[key] = date.fromisoformat(pricing[key])
        self.pricing = Pricing(**pricing)
        today = date.today()
        if self.pricing.model != settings.code_analysis_model:
            raise ValueError("Provider pricing model differs from the selected model")
        if not self.pricing.verified_on <= today <= self.pricing.valid_until:
            raise ValueError("Current provider pricing is required")
        if not today - timedelta(days=7) <= self.pricing.exchange_date <= today:
            raise ValueError("A recent USD/PLN conversion is required")
        rates = (
            self.pricing.input_usd_per_million,
            self.pricing.output_usd_per_million,
            self.pricing.usd_pln,
            raw["reservation_pln"],
        )
        if any(not math.isfinite(value) or value <= 0 for value in rates):
            raise ValueError("Provider allowance and rates must be finite and positive")
        self.reservation = raw["reservation_pln"]
        minimum = (
            self.pricing.cost(settings.request_tokens + 4096, settings.output_tokens * 2)
            * settings.code_analysis_turn_limit
            * 1.5
        )
        if self.reservation < minimum:
            raise ValueError("Provider reservation does not include conservative turn headroom")
        limits = [
            limit
            for limit in (settings.budget_pln, raw.get("authorized_budget_pln"))
            if limit is not None
        ]
        if any(not math.isfinite(limit) or limit <= 0 for limit in limits):
            raise ValueError("Configured provider limits must be finite and positive")
        self.ledger = BudgetLedger(settings.budget_ledger, min(limits) if limits else None)
        self.run_id = run_id
        self.provider = raw["provider"]
        self.authorization = raw["authorization_ref"]

    def reserve(self, provider, model, request_id):
        if (provider, model) != (self.provider, self.pricing.model):
            raise ValueError("Provider reservation identity mismatch")
        return self.ledger.reserve(
            self.run_id,
            f"code-analysis:{provider}:{request_id}",
            self.reservation,
            self.pricing,
        )

    def settle(self, reservation, usage):
        valid = isinstance(usage, dict) and all(
            isinstance(usage.get(key), int) and usage[key] >= 0
            for key in ("input_tokens", "output_tokens")
        )
        cost = self.pricing.cost(usage["input_tokens"], usage["output_tokens"]) if valid else None
        self.ledger.settle(
            reservation,
            cost,
            {
                "provider": self.provider,
                "authorization_ref": self.authorization,
                "usage": usage if valid else None,
            },
        )
