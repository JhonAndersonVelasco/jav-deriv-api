"""
Example 3 — Real-time subscriptions (balance stream + custom ticks stream).

Requires a valid Deriv API token.

Run:
    DERIV_TOKEN=your_token python -m deriv_api.examples.03_subscriptions
"""

import asyncio
import os
import signal

from deriv_api import DerivAPI, DerivRequestError

APP_ID = 1089
TOKEN = os.environ.get("DERIV_TOKEN", "")


async def watch_balance(api: DerivAPI, stop: asyncio.Event) -> None:
    """Stream balance updates until the stop event is set."""
    print("[balance] Subscribing to balance updates…")
    stream_id: str | None = None
    try:
        async for update in api.stream_balance():
            stream_id = update.subscription_id
            print(f"[balance] {update.balance:.2f} {update.currency}  (sub_id={stream_id})")
            if stop.is_set():
                break
    finally:
        if stream_id:
            cancelled = await api.forget(stream_id)
            print(f"[balance] Stream cancelled: {cancelled}")


async def watch_ticks(api: DerivAPI, symbol: str, stop: asyncio.Event) -> None:
    """Stream raw tick data for a symbol until the stop event is set."""
    print(f"[ticks ] Subscribing to ticks for {symbol}…")
    sub_id: str | None = None
    count = 0
    try:
        async for msg in api.subscribe({"ticks": symbol, "subscribe": 1}):
            tick = msg.get("tick", {})
            sub_id = msg.get("subscription", {}).get("id")
            if tick:
                count += 1
                print(
                    f"[ticks ] {symbol}  quote={tick.get('quote')}  "
                    f"epoch={tick.get('epoch')}  (#{count})"
                )
            if stop.is_set() or count >= 10:
                break
    finally:
        if sub_id:
            cancelled = await api.forget(sub_id)
            print(f"[ticks ] Stream cancelled: {cancelled}")


async def main() -> None:
    if not TOKEN:
        print("Set the DERIV_TOKEN environment variable before running this example.")
        return

    stop = asyncio.Event()

    # Graceful shutdown on Ctrl-C
    loop = asyncio.get_event_loop()
    loop.add_signal_handler(signal.SIGINT, stop.set)

    async with DerivAPI(app_id=APP_ID, token=TOKEN) as api:
        print("Connected. Running subscriptions for up to 30 seconds (Ctrl-C to stop early).\n")

        # Run balance stream and tick stream concurrently
        balance_task = asyncio.create_task(watch_balance(api, stop))
        ticks_task = asyncio.create_task(watch_ticks(api, "R_50", stop))

        # Auto-stop after 30 seconds
        async def auto_stop() -> None:
            await asyncio.sleep(30)
            stop.set()

        await asyncio.gather(
            asyncio.create_task(auto_stop()),
            balance_task,
            ticks_task,
            return_exceptions=True,
        )

    print("\nDone.")


if __name__ == "__main__":
    asyncio.run(main())
