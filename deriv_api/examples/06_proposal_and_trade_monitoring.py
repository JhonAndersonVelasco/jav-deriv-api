"""
Example 06 — Real-time options trading lifecycle: Proposal, Buy, and Live Contract Monitoring.

Demonstrates the complete end-to-end trading flow on Deriv:
1. Initialize authenticated session (DerivAPI with automatic OTP).
2. Request a live price proposal for a Rise (CALL) contract on R_50.
3. Buy the contract using the proposal ID.
4. Stream real-time contract progress (spot price, tick updates, unrealized P&L).
5. Detect contract settlement (Won/Lost) and final payout.

Run:
    DERIV_TOKEN=your_token python -m deriv_api.examples.06_proposal_and_trade_monitoring
"""

import asyncio
import os

from deriv_api import DerivAPI

TOKEN = os.environ.get("DERIV_TOKEN")


async def main() -> None:
    if not TOKEN:
        print("Please set the DERIV_TOKEN environment variable before running this example.")
        print("Example: export DERIV_TOKEN='pat_...'")
        return

    symbol = "R_50"
    contract_type = "CALL"  # Rise
    stake = 1.00  # 1.00 USD
    duration = 5  # 5 ticks

    print("==================================================================")
    print("Deriv Options Trading Lifecycle: Proposal → Buy → Live Monitoring")
    print("==================================================================")

    async with DerivAPI(token=TOKEN) as api:
        # ── Step 1: Account & initial balance ──────────────────────────
        initial_balance = await api.get_balance()
        print(f"\n[1] Connected to Account : {initial_balance.loginid}")
        print(
            f"    Initial Balance      : {initial_balance.balance:.2f} {initial_balance.currency}"
        )

        # ── Step 2: Request price proposal ─────────────────────────────
        print(
            f"\n[2] Requesting price proposal for {contract_type} on {symbol} "
            f"({duration} ticks, {stake:.2f} USD)..."
        )
        prop = await api.get_proposal(
            contract_type=contract_type,
            currency=initial_balance.currency,
            underlying_symbol=symbol,
            amount=stake,
            basis="stake",
            duration=duration,
            duration_unit="t",
            subscribe=True,  # Keeps session cached for buying
        )
        print(f"    Proposal ID : {prop.id}")
        print(f"    Ask Price   : {prop.ask_price:.2f} {initial_balance.currency}")
        print(f"    Max Payout  : {prop.payout:.2f} {initial_balance.currency}")
        print(f"    Spot Quote  : {prop.spot}")

        # ── Step 3: Execute buy ────────────────────────────────────────
        print(f"\n[3] Purchasing contract at {prop.ask_price:.2f} {initial_balance.currency}…")
        receipt = await api.buy(prop.id, price=prop.ask_price)
        print("    ✓ Purchase Confirmed!")
        print(f"    Contract ID : {receipt.contract_id}")
        print(f"    Balance Now : {receipt.balance_after:.2f} {initial_balance.currency}")

        # ── Step 4: Stream live contract updates ───────────────────────
        print(f"\n[4] Monitoring contract {receipt.contract_id} in real time...")
        print(f"    {'Status':<10} {'Current Spot':<14} {'Profit / Loss':<15} {'Settled'}")
        print("    " + "-" * 50)

        sub_id = None
        final_status = "UNKNOWN"
        final_profit = 0.0

        async for update in api.stream_proposal_open_contract(receipt.contract_id):
            sub_id = update.get("subscription", {}).get("id")
            poc = update.get("proposal_open_contract", {})

            status = poc.get("status", "open")
            raw_spot = poc.get("current_spot")
            current_spot = float(raw_spot) if raw_spot is not None else 0.0
            raw_profit = poc.get("profit")
            profit = float(raw_profit) if raw_profit is not None else 0.0
            is_sold = bool(poc.get("is_sold", 0))

            profit_sign = f"+{profit:.2f}" if profit > 0 else f"{profit:.2f}"
            settled_flag = "YES" if is_sold else "NO"
            print(
                f"    {status.upper():<10} {current_spot:<14.4f} {profit_sign:<15} {settled_flag}"
            )

            if is_sold:
                final_status = status
                final_profit = profit
                break

        # Cleanup stream subscription
        if sub_id:
            try:
                await api.forget(sub_id)
            except Exception:
                pass

        # ── Step 5: Final summary ──────────────────────────────────────
        final_balance = await api.get_balance()
        badge = "🎉" if final_status == "won" else "📉"
        print("\n==================================================================")
        print(f"Contract Result   : {final_status.upper()} {badge}")
        profit_prefix = "+" if final_profit >= 0 else ""
        print(f"Net Profit / Loss : {profit_prefix}{final_profit:.2f} {final_balance.currency}")
        print(f"Final Balance     : {final_balance.balance:.2f} {final_balance.currency}")
        print("==================================================================")


if __name__ == "__main__":
    asyncio.run(main())
