"""
Example 1 — List active trading symbols and their available contract types.

No authentication required.

Run:
    python -m deriv_api.examples.01_active_symbols
"""

import asyncio
from deriv_api import DerivAPI

APP_ID = 1089  # Deriv's public demo app_id

# Maps Deriv contract_category values to friendly labels
CATEGORY_LABELS: dict[str, str] = {
    "accumulator":        "Accumulators",
    "asian":              "Asians",
    "callputequal":       "Rise/Fall Equal",
    "callputspread":      "Call/Put Spread",
    "digits":             "Digits",
    "highlowticks":       "High/Low Ticks",
    "lookback":           "Lookbacks",
    "multiplier":         "Multipliers",
    "reset":              "Resets",
    "runs":               "Only Ups/Downs",
    "smarttrader":        "SmartTrader",
    "touchnotouch":       "Touch/No Touch",
    "vanilla":            "Vanillas",
    "callput":            "Rise/Fall",
}


async def get_contract_categories(api: DerivAPI, symbol: str) -> tuple[str, list[str]]:
    """Return (symbol, [category_label, ...]) for a given symbol."""
    try:
        data = await api.get_contracts_for(symbol)
        available = data.get("available", [])
        # Collect unique categories preserving order
        seen: set[str] = set()
        categories: list[str] = []
        for contract in available:
            cat = contract.get("contract_category", "")
            if cat and cat not in seen:
                seen.add(cat)
                categories.append(CATEGORY_LABELS.get(cat, cat))
        return symbol, categories
    except Exception:
        return symbol, []


async def main() -> None:
    async with DerivAPI(app_id=APP_ID) as api:
        # ── Step 1: fetch all active symbols ────────────────────────────
        print("Fetching active symbols (brief mode)…")
        symbols = await api.get_active_symbols(mode="brief")
        print(f"Found {len(symbols)} active symbols.\n")

        print(f"{'Symbol':<20} {'Name':<35} {'Market':<20} {'Open'}")
        print("-" * 82)
        for s in symbols:
            open_status = "✓" if s.exchange_is_open else "✗"
            print(f"{s.symbol:<20} {s.display_name:<35} {s.market:<20} {open_status}")

        # ── Step 2: fetch contract types for all symbols in parallel ────
        print("\n\nFetching available contract types per symbol…")
        tasks = [get_contract_categories(api, s.symbol) for s in symbols]
        results: list[tuple[str, list[str]]] = await asyncio.gather(*tasks)

        # Build a lookup: symbol → display_name
        name_map = {s.symbol: s.display_name for s in symbols}

        print(f"\n{'Symbol':<20} {'Name':<35} {'Contract Types'}")
        print("-" * 100)
        for sym, categories in sorted(results, key=lambda x: x[0]):
            cats_str = ", ".join(categories) if categories else "—"
            print(f"{sym:<20} {name_map.get(sym, ''):<35} {cats_str}")


if __name__ == "__main__":
    asyncio.run(main())
