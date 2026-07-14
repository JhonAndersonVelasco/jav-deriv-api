"""
Example 4 — REST API: account management.

Requires a valid Deriv API token and your App ID.

Run:
    DERIV_APP_ID=your_app_id DERIV_TOKEN=your_token \
        python -m deriv_api.examples.04_rest_accounts
"""

import asyncio
import os

from deriv_api import DerivRestClient, DerivAuthError, DerivRequestError

APP_ID = os.environ.get("DERIV_APP_ID", "1089")
TOKEN = os.environ.get("DERIV_TOKEN", "")


async def main() -> None:
    if not TOKEN:
        print("Set DERIV_TOKEN before running this example.")
        return

    async with DerivRestClient(app_id=APP_ID, token=TOKEN) as rest:

        # --- Health check (no auth required) ---
        print("Checking API health…")
        ok = await rest.health()
        print(f"  API is {'healthy ✓' if ok else 'unhealthy ✗'}\n")

        # --- Get accounts ---
        print("Fetching accounts…")
        try:
            accounts = await rest.get_accounts()
            if not accounts:
                print("  No accounts found.")
            else:
                print(f"  {'Account ID':<15} {'Type':<8} {'Status':<10} {'Balance':>10}  Currency")
                print("  " + "-" * 55)
                for acc in accounts:
                    print(
                        f"  {acc.account_id:<15} {acc.account_type:<8} {acc.status:<10} "
                        f"{acc.balance:>10.2f}  {acc.currency}"
                    )
        except DerivAuthError as e:
            print(f"  Auth error: {e.message}")
            return

        # --- Create a demo account (idempotent — safe to call repeatedly) ---
        print("\nCreating (or fetching existing) demo account…")
        try:
            result = await rest.create_account(account_type="demo")
            if isinstance(result, list):
                print(f"  Created {len(result)} new account(s):")
                for acc in result:
                    print(f"    {acc.account_id}  {acc.account_type}  {acc.currency}")
            else:
                print(f"  Account already exists: {result.account_id} ({result.status})")
        except DerivRequestError as e:
            print(f"  Could not create account: [{e.code}] {e.message}")

        # --- Legacy migration status ---
        print("\nChecking legacy migration status…")
        try:
            status = await rest.get_legacy_migration_status()
            print(f"  Migration status: {status}")
        except DerivAuthError:
            print("  (Not available for this token)")


if __name__ == "__main__":
    asyncio.run(main())
