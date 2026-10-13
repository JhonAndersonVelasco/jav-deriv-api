"""
Example 4 — REST API: account management and OTP generation.

Demonstrates the HTTP REST client for the Deriv Options API:
- Health check (unauthenticated)
- Account listing (using PAT as Bearer token with Deriv-App-ID)
- Querying migration status
- Generating a pre-authorized OTP WebSocket URL for trading

Run:
    DERIV_TOKEN=your_token python -m deriv_api.examples.04_rest_accounts
"""

import asyncio
import os

from deriv_api import DerivAuthError, DerivRequestError, DerivRestClient

# DERIV_APP_ID is loaded automatically from deriv_api/.env if not provided in environment
APP_ID = os.environ.get("DERIV_APP_ID")
# Personal Access Tokens (PAT) work directly as Bearer tokens in the Deriv Options API
TOKEN = os.environ.get("DERIV_TOKEN") or os.environ.get("DERIV_OAUTH_TOKEN", "")


async def main() -> None:
    # ── Step 1: Health check (no auth required) ───────────────────────
    print("1. Checking Deriv API health…")
    async with DerivRestClient(app_id=APP_ID) as rest:
        ok = await rest.health()
        print(f"   API status: {'healthy ✓' if ok else 'unhealthy ✗'}\n")

    if not TOKEN:
        print(
            "Please set the DERIV_TOKEN environment variable to test authenticated REST endpoints."
        )
        print("Example: export DERIV_TOKEN='pat_...'")
        return

    # ── Step 2: Query accounts with Bearer token + Deriv-App-ID ────────
    print("2. Fetching account information via REST…")
    async with DerivRestClient(app_id=APP_ID, token=TOKEN) as rest:
        try:
            accounts = await rest.get_accounts()
            if not accounts:
                print("   No accounts found for this token.")
                return

            print(f"   {'Account ID':<15} {'Type':<8} {'Status':<10} {'Balance':>10}  Currency")
            print("   " + "-" * 55)
            target_demo_account = None
            for acc in accounts:
                print(
                    f"   {acc.account_id:<15} {acc.account_type:<8} {acc.status:<10} "
                    f"{acc.balance:>10.2f}  {acc.currency}"
                )
                if acc.account_type == "demo" or acc.account_id.startswith("D"):
                    target_demo_account = acc.account_id

            if not target_demo_account and accounts:
                target_demo_account = accounts[0].account_id

        except DerivAuthError as e:
            print(f"   Auth error: {e.message}")
            return

        # ── Step 3: Platform upgrade / migration status ───────────────
        print("\n3. Checking legacy migration status…")
        try:
            status = await rest.get_legacy_migration_status()
            print(f"   Migration status: {status}")
        except Exception as e:
            print(f"   Migration status: {e}")

        # ── Step 4: Request OTP WebSocket URL ─────────────────────────
        if target_demo_account:
            print(f"\n4. Generating pre-authorized OTP WebSocket URL for {target_demo_account}…")
            try:
                otp_url = await rest.get_otp_url(target_demo_account)
                print("   OTP URL generated successfully!")
                print(f"   URL: {otp_url[:65]}...")
                print("   (This URL is ready to pass to DerivAPI(endpoint=otp_url) for trading)")
            except DerivRequestError as e:
                print(f"   Could not generate OTP URL: [{e.code}] {e.message}")


if __name__ == "__main__":
    asyncio.run(main())
