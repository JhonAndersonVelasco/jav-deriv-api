"""
Example 1 — List active trading symbols and their available contract types.

Works with both anonymous connections (public symbols) and authenticated
accounts (providing full catalog via OTP when DERIV_TOKEN is set).

Run:
    python -m deriv_api.examples.01_active_symbols
    # Or with token for full account catalog:
    DERIV_TOKEN=your_token python -m deriv_api.examples.01_active_symbols
"""

import asyncio
import os

from deriv_api import DerivAPI

TOKEN = os.environ.get("DERIV_TOKEN")

# Maps Deriv contract_category values to friendly labels
CATEGORY_LABELS: dict[str, str] = {
    "accumulator": "Accumulators",
    "asian": "Asians",
    "callputequal": "Rise/Fall Equal",
    "callputspread": "Call/Put Spread",
    "digits": "Digits",
    "highlowticks": "High/Low Ticks",
    "lookback": "Lookbacks",
    "multiplier": "Multipliers",
    "reset": "Resets",
    "runs": "Only Ups/Downs",
    "smarttrader": "SmartTrader",
    "touchnotouch": "Touch/No Touch",
    "vanilla": "Vanillas",
    "callput": "Rise/Fall",
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
    # If DERIV_TOKEN is provided, DerivAPI automatically resolves the OTP session
    if TOKEN:
        print("Connecting to Deriv using account authentication (OTP)...")
        api_ctx = DerivAPI(token=TOKEN)
    else:
        print("Connecting to Deriv anonymously (public demo mode)...")
        api_ctx = DerivAPI(app_id=1089)

    async with api_ctx as api:
        # Check server status
        server_time = await api.get_server_time()
        print(f"Connected to Deriv! Server time (epoch): {server_time}\n")

        # ── Step 1: fetch active symbols ───────────────────────────────
        print("Fetching active symbols (brief mode)…")
        symbols = await api.get_active_symbols(mode="brief")

        if not symbols:
            print("No public symbols returned for anonymous connection in this region.")
            print(
                "Tip: Define DERIV_TOKEN in your environment "
                "to load the full account symbol catalog."
            )
            return

        print(f"Found {len(symbols)} active symbols.\n")
        print(f"{'Symbol':<20} {'Name':<35} {'Market':<20} {'Open'}")
        print("-" * 82)
        for s in symbols[:25]:  # Display first 25 symbols
            open_status = "✓" if s.exchange_is_open else "✗"
            print(f"{s.symbol:<20} {s.display_name:<35} {s.market:<20} {open_status}")

        if len(symbols) > 25:
            print(f"... and {len(symbols) - 25} more symbols.")

        # ── Step 2: fetch contract types for top 10 symbols ─────────────
        top_symbols = symbols[:10]
        print(f"\nFetching available contract types for top {len(top_symbols)} symbols…")
        tasks = [get_contract_categories(api, s.symbol) for s in top_symbols]
        results: list[tuple[str, list[str]]] = await asyncio.gather(*tasks)

        name_map = {s.symbol: s.display_name for s in top_symbols}

        print(f"\n{'Symbol':<20} {'Name':<35} {'Contract Types'}")
        print("-" * 100)
        for sym, categories in sorted(results, key=lambda x: x[0]):
            cats_str = ", ".join(categories) if categories else "—"
            print(f"{sym:<20} {name_map.get(sym, ''):<35} {cats_str}")


if __name__ == "__main__":
    asyncio.run(main())
