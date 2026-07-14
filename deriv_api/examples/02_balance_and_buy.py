"""
Example 2 — Check balance and buy a contract.

Requires a valid Deriv API token with 'trade' scope.

Run:
    DERIV_TOKEN=your_token python -m deriv_api.examples.02_balance_and_buy
"""

import asyncio
import os
from pathlib import Path

from dotenv import load_dotenv

from deriv_api import DerivAPI, BuyParameters, DerivAuthError, DerivRequestError

# Load .env from the deriv_api package directory (one level up from examples/)
load_dotenv(Path(__file__).parent.parent / ".env")

APP_ID = 1089
TOKEN = os.environ.get("DERIV_TOKEN", "")


async def main() -> None:
    if not TOKEN:
        print("Set the DERIV_TOKEN environment variable before running this example.")
        return

    async with DerivAPI(app_id=APP_ID, token=TOKEN) as api:

        # --- Balance ---
        print("Fetching account balance…")
        balance = await api.get_balance()
        print(f"  Login ID : {balance.loginid}")
        print(f"  Balance  : {balance.balance:.2f} {balance.currency}\n")

        # --- Contracts list ---
        print("Available contract categories:")
        categories = await api.get_contracts_list()
        for cat in categories:
            types = ", ".join(cat.contract_types[:4])
            if len(cat.contract_types) > 4:
                types += f" … (+{len(cat.contract_types) - 4} more)"
            print(f"  {cat.display_name:<30} [{types}]")

        # --- Contracts for a symbol ---
        symbol = "R_50"
        print(f"\nFetching contracts for {symbol}…")
        cf = await api.get_contracts_for(symbol)
        available = cf.get("available", [])
        print(f"  {len(available)} contract types available for {symbol}.")

        # --- Buy a small demo contract (Rise/Fall, 1 USD, 5 ticks) ---
        print("\nBuying a CALL contract on R_50 (5 ticks, 1 USD stake)…")
        params = BuyParameters(
            contract_type="CALL",
            currency="USD",
            underlying_symbol="R_50",
            amount=1.0,
            basis="stake",
            duration=5,
            duration_unit="t",
        )
        try:
            receipt = await api.buy_with_parameters(params, price=1.0)
            print(f"  Contract ID  : {receipt.contract_id}")
            print(f"  Buy price    : {receipt.buy_price:.4f} {balance.currency}")
            print(f"  Payout       : {receipt.payout:.4f} {balance.currency}")
            print(f"  Balance after: {receipt.balance_after:.2f} {balance.currency}")
            print(f"  Description  : {receipt.longcode}")
        except DerivRequestError as e:
            print(f"  Could not buy contract: [{e.code}] {e.message}")


if __name__ == "__main__":
    asyncio.run(main())
