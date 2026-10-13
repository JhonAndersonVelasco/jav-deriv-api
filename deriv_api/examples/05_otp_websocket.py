"""
Example 05: Authenticated Options Trading via OTP (New Deriv API).

Demonstrates the step-by-step authentication flow for Personal Access Tokens (PAT):
1. Use DerivRestClient with your PAT and registered Deriv-App-ID.
2. Query accounts and balances via GET /trading/v1/options/accounts.
3. Request a one-time password (OTP) URL via POST /trading/v1/options/accounts/{accountId}/otp.
4. Connect DerivAPI directly to the OTP URL (pre-authenticated WebSocket) to stream/trade.

Run:
    DERIV_TOKEN=your_token python -m deriv_api.examples.05_otp_websocket
"""

import asyncio
import os

from deriv_api import DerivAPI, DerivRestClient

TOKEN = os.environ.get("DERIV_TOKEN")


async def main() -> None:
    if not TOKEN:
        print("Aviso: DERIV_TOKEN no está definido en el entorno de la aplicación.")
        print("Por favor defínelo en el .env de tu aplicación o con: export DERIV_TOKEN='tu_token'")
        return

    # ------------------------------------------------------------------
    # Step 1 & 2: REST Client to list accounts and balances
    # ------------------------------------------------------------------
    print("1. Consultando cuentas y balances vía REST...")
    async with DerivRestClient(token=TOKEN) as rest:
        accounts = await rest.get_accounts()
        if not accounts:
            print("No se encontraron cuentas activas.")
            return

        for acc in accounts:
            print(
                f"   Cuenta: {acc.account_id:<12} | "
                f"Balance: {acc.balance:>10.2f} {acc.currency} ({acc.account_type})"
            )

        # Seleccionar preferentemente la cuenta Demo para pruebas seguras
        demo_accounts = [
            a for a in accounts if a.account_type == "demo" or a.account_id.startswith("D")
        ]
        target_account = demo_accounts[0] if demo_accounts else accounts[0]
        print(
            f"\n2. Solicitando URL WebSocket OTP para la cuenta "
            f"{target_account.account_id} ({target_account.account_type})..."
        )

        # --------------------------------------------------------------
        # Step 3: Generar OTP WebSocket URL
        # --------------------------------------------------------------
        ws_otp_url = await rest.get_otp_url(target_account.account_id)
        print(f"   URL OTP obtenida: {ws_otp_url[:55]}...")

    # ------------------------------------------------------------------
    # Step 4: Conectar WebSocket pre-autenticado con la URL OTP
    # ------------------------------------------------------------------
    print("\n3. Conectando al WebSocket de Deriv con la URL OTP pre-autenticada...")
    async with DerivAPI(endpoint=ws_otp_url) as api:
        print("   ¡Conexión establecida y autorizada automáticamente!")

        server_time = await api.get_server_time()
        print(f"   Hora del servidor Deriv: {server_time}")

        balance = await api.get_balance()
        print(f"   Balance confirmado por WebSocket: {balance.balance:.2f} {balance.currency}")


if __name__ == "__main__":
    asyncio.run(main())
