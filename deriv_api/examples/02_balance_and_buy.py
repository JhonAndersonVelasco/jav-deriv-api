"""
Example 2 — Check balance, query contracts, and buy an option contract.

Requires a valid Deriv API token (Personal Access Token - PAT).
When using a PAT, DerivAPI automatically resolves the OTP WebSocket connection.

Run:
    DERIV_TOKEN=your_token python -m deriv_api.examples.02_balance_and_buy
"""

import asyncio
import os

from deriv_api import BuyParameters, DerivAPI, DerivAuthError, DerivRequestError

TOKEN = os.environ.get("DERIV_TOKEN", "")


async def main() -> None:
    if not TOKEN:
        print("Please set the DERIV_TOKEN environment variable before running this example.")
        print("Example: export DERIV_TOKEN='pat_...'")
        return

    print("Connecting to Deriv and initializing authenticated trading session...")
    async with DerivAPI(token=TOKEN) as api:
        # ── Step 1: Check account balance ──────────────────────────────
        print("\n1. Fetching account balance…")
        balance = await api.get_balance()
        print(f"  Account ID : {balance.loginid}")
        print(f"  Balance    : {balance.balance:.2f} {balance.currency}")

        # ── Step 2: Query available contracts for R_50 ─────────────────
        symbol = "R_50"
        print(f"\n2. Fetching available contract types for {symbol}…")
        cf = await api.get_contracts_for(symbol)
        available = cf.get("available", [])
        seen: set[str] = set()
        for c in available:
            cat = c.get("contract_category_display", c.get("contract_category", ""))
            if cat and cat not in seen:
                seen.add(cat)
                types_in_cat = [
                    x.get("contract_type", "")
                    for x in available
                    if x.get("contract_category") == c.get("contract_category")
                ]
                print(f"  {cat:<30} {', '.join(dict.fromkeys(types_in_cat))}")

        # ── Step 3: Buy a demo Rise (CALL) contract (1 USD, 5 ticks) ───
        print(f"\n3. Buying a Rise (CALL) contract on {symbol} (5 ticks, 1.00 USD stake)…")
        params = BuyParameters(
            contract_type="CALL",
            currency="USD",
            symbol=symbol,
            amount=1.0,
            basis="stake",
            duration=5,
            duration_unit="t",
        )
        try:
            receipt = await api.buy_with_parameters(params, price=1.0)
            print("  ✓ Purchase confirmed!")
            print(f"  Contract ID  : {receipt.contract_id}")
            print(f"  Buy price    : {receipt.buy_price:.2f} {balance.currency}")
            print(f"  Payout       : {receipt.payout:.2f} {balance.currency}")
            print(f"  Balance after: {receipt.balance_after:.2f} {balance.currency}")
            print(f"  Description  : {receipt.longcode}")
        except (DerivRequestError, DerivAuthError) as e:
            print(f"  Could not buy contract: [{getattr(e, 'code', 'error')}] {e.message}")


if __name__ == "__main__":
    asyncio.run(main())
