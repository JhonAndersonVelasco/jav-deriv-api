"""
Example 4 — REST API: account management.

IMPORTANT — Authentication:
  The REST API requires an OAuth2 Bearer token, which is DIFFERENT from the
  Personal Access Token (PAT) used in the WebSocket examples.

  To obtain an OAuth2 token:
    1. Register your app at https://developers.deriv.com
    2. Implement the OAuth2 Authorization Code + PKCE flow:
       - Authorization: https://auth.deriv.com/oauth2/auth
       - Token:         https://auth.deriv.com/oauth2/token
    3. Use the resulting access token as DERIV_OAUTH_TOKEN

  The PAT in DERIV_TOKEN works for WebSocket auth (examples 02, 03) but NOT here.

Run:
    DERIV_APP_ID=your_app_id DERIV_OAUTH_TOKEN=your_oauth_token \\
        python -m deriv_api.examples.04_rest_accounts
"""

import asyncio
import os

from jav_deriv_api import DerivRestClient, DerivAuthError, DerivRequestError

APP_ID = os.environ.get("DERIV_APP_ID", "1089")
# OAuth2 Bearer token — distinct from the PAT used in WebSocket examples
OAUTH_TOKEN = os.environ.get("DERIV_OAUTH_TOKEN", "")


async def main() -> None:
    # --- Health check (no auth required) ---
    print("Checking API health…")
    async with DerivRestClient(app_id=APP_ID) as rest:
        ok = await rest.health()
        print(f"  API is {'healthy ✓' if ok else 'unhealthy ✗'}\n")

    if not OAUTH_TOKEN:
        print(
            "DERIV_OAUTH_TOKEN is not set.\n"
            "The REST API requires an OAuth2 Bearer token (not the PAT from DERIV_TOKEN).\n"
            "See the module docstring for instructions."
        )
        return

    async with DerivRestClient(app_id=APP_ID, token=OAUTH_TOKEN) as rest:

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
