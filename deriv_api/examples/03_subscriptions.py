"""
Example 3 — Real-time subscriptions (balance stream + ticks stream).

Requires a valid Deriv API token (Personal Access Token - PAT).
Demonstrates concurrent asynchronous streaming of real-time ticks and balance updates.

Run:
    DERIV_TOKEN=your_token python -m deriv_api.examples.03_subscriptions
"""

import asyncio
import os
import signal
import sys

from deriv_api import DerivAPI

TOKEN = os.environ.get("DERIV_TOKEN", "")


async def watch_balance(api: DerivAPI, stop: asyncio.Event) -> None:
    """Stream balance updates until the stop event is set."""
    print("[balance] Subscribing to live balance updates…")
    stream_id: str | None = None
    try:
        async for update in api.stream_balance():
            stream_id = update.subscription_id
            print(
                f"[balance] Account {update.loginid}: {update.balance:.2f} "
                f"{update.currency} (sub_id={stream_id})"
            )
            if stop.is_set():
                break
    except asyncio.CancelledError:
        pass
    finally:
        if stream_id:
            try:
                await api.forget(stream_id)
                print(f"[balance] Stream cancelled: {stream_id}")
            except Exception:
                pass


async def watch_ticks(
    api: DerivAPI,
    symbol: str,
    stop: asyncio.Event,
    max_ticks: int = 5,
) -> None:
    """Stream real-time tick data for a symbol until max_ticks are received or stopped."""
    print(f"[ticks  ] Subscribing to live ticks for {symbol}…")
    sub_id: str | None = None
    count = 0
    try:
        async for tick in api.stream_ticks(symbol):
            sub_id = tick.subscription_id
            count += 1
            print(
                f"[ticks  ] #{count:02d} | {tick.symbol:<6} | "
                f"Quote: {tick.quote:<10.4f} | Epoch: {tick.epoch}"
            )
            if stop.is_set() or count >= max_ticks:
                break
    except asyncio.CancelledError:
        pass
    finally:
        if sub_id:
            try:
                await api.forget(sub_id)
                print(f"[ticks  ] Stream cancelled: {sub_id}")
            except Exception:
                pass


async def main() -> None:
    if not TOKEN:
        print("Please set the DERIV_TOKEN environment variable before running this example.")
        print("Example: export DERIV_TOKEN='pat_...'")
        return

    stop = asyncio.Event()

    # Graceful shutdown handler for Ctrl-C
    loop = asyncio.get_running_loop()
    if sys.platform != "win32":
        for sig in (signal.SIGINT, signal.SIGTERM):
            loop.add_signal_handler(sig, stop.set)

    print("Connecting to Deriv authenticated WebSocket session...")
    async with DerivAPI(token=TOKEN) as api:
        print("Connected! Streaming balance updates and ticks for R_50...\n")

        # Run balance stream and tick stream concurrently
        balance_task = asyncio.create_task(watch_balance(api, stop))
        ticks_task = asyncio.create_task(watch_ticks(api, "R_50", stop, max_ticks=5))

        # Wait for the tick stream to finish (or stop event)
        await ticks_task

        # Signal stop for any remaining tasks
        stop.set()
        balance_task.cancel()
        try:
            await balance_task
        except asyncio.CancelledError:
            pass

    print("\nSubscriptions finished successfully.")


if __name__ == "__main__":
    asyncio.run(main())
