# jav-deriv-api

Async Python client library for the [Deriv](https://deriv.com) trading API.

Covers the full WebSocket API (real-time prices, options trading, subscriptions, automatic OTP authentication) and the REST HTTP API (account management and OTP generation). Built on top of `websockets` and `aiohttp`. Requires Python ≥ 3.10.

> **Package names**: Both `import deriv_api` and `import jav_deriv_api` are supported out of the box!

---

## Installation

```bash
pip install jav-deriv-api
```

After installation, you can optionally run the interactive setup wizard to configure your `.env` file:

```bash
deriv-setup
```

---

## Authentication in the New Deriv Options API

Deriv v2 uses a modern authentication model:
1. **Public queries** (server time, active symbols, basic ticks) do not require a token.
2. **Personal Access Tokens (PAT)** (e.g. `pat_...`) are authenticated as Bearer tokens in HTTPS REST requests with your registered `Deriv-App-ID`.
3. **Options Trading & Balance** require a WebSocket URL with an OTP parameter (`POST /trading/v1/options/accounts/{accountId}/otp`).
4. **`jav-deriv-api` handles this automatically**:
   - Simply pass `DerivAPI(token=TOKEN)`: the library queries your accounts via REST, picks your Demo account (or specified `account_id`), obtains the OTP URL, and connects seamlessly!
   - You can also specify `endpoint=otp_url` or use `DerivRestClient` directly if you prefer manual control.

---

## Quick start

### 1. Active symbols (public or authenticated)

```python
import asyncio
from deriv_api import DerivAPI


async def main():
    # Pass token to load full account symbol catalog, or leave empty for public demo
    async with DerivAPI() as api:
        time = await api.get_server_time()
        print("Server epoch:", time)

        symbols = await api.get_active_symbols(mode="brief")
        for s in symbols[:5]:
            print(s.symbol, s.display_name, s.market)


asyncio.run(main())
```

### 2. Balance and buy a contract (automatic OTP)

```python
import asyncio
from deriv_api import DerivAPI, BuyParameters


async def main():
    # When passing a PAT, DerivAPI automatically resolves the OTP WebSocket session
    async with DerivAPI(token="YOUR_PAT_TOKEN") as api:
        balance = await api.get_balance()
        print(f"Account {balance.loginid}: {balance.balance:.2f} {balance.currency}")

        params = BuyParameters(
            contract_type="CALL",
            currency="USD",
            symbol="R_50",
            amount=1.0,
            basis="stake",
            duration=5,
            duration_unit="t",
        )
        receipt = await api.buy_with_parameters(params, price=1.0)
        print(
            f"Contract ID: {receipt.contract_id} bought for {receipt.buy_price} {balance.currency}"
        )
        print(f"Balance after trade: {receipt.balance_after:.2f} {balance.currency}")


asyncio.run(main())
```

### 3. Price proposal and live trade monitoring

```python
import asyncio
from deriv_api import DerivAPI


async def main():
    async with DerivAPI(token="YOUR_PAT_TOKEN") as api:
        # Step 1: Request active price proposal
        prop = await api.get_proposal(
            contract_type="CALL",
            currency="USD",
            symbol="R_50",
            amount=1.0,
            basis="stake",
            duration=5,
            duration_unit="t",
            subscribe=True,
        )
        print(f"Proposal ID: {prop.id} | Ask: {prop.ask_price} | Payout: {prop.payout}")

        # Step 2: Buy from proposal
        receipt = await api.buy(prop.id, price=prop.ask_price)
        print(f"Purchased contract: {receipt.contract_id}")

        # Step 3: Stream open contract updates until settled
        async for update in api.stream_proposal_open_contract(receipt.contract_id):
            poc = update.get("proposal_open_contract", {})
            status = poc.get("status")
            spot = poc.get("current_spot")
            profit = poc.get("profit")
            is_sold = bool(poc.get("is_sold", 0))

            print(f"Status: {status} | Spot: {spot} | P&L: {profit}")
            if is_sold:
                print(f"Contract Settled! Result: {status.upper()} | Profit: {profit}")
                break


asyncio.run(main())
```

### 4. Real-time tick & balance streaming

```python
import asyncio
from deriv_api import DerivAPI


async def main():
    async with DerivAPI(token="YOUR_PAT_TOKEN") as api:
        # Stream live ticks
        async for tick in api.stream_ticks("R_50"):
            print(f"{tick.symbol} quote={tick.quote} epoch={tick.epoch}")
            await api.forget(tick.subscription_id)
            break

        # Stream balance updates
        async for update in api.stream_balance():
            print(f"Balance update: {update.balance:.2f} {update.currency}")
            await api.forget(update.subscription_id)
            break


asyncio.run(main())
```

### 5. REST API — accounts and OTP generation

```python
import asyncio
from deriv_api import DerivRestClient


async def main():
    async with DerivRestClient(token="YOUR_PAT_TOKEN") as rest:
        # Health check
        ok = await rest.health()
        print("API healthy:", ok)

        # List trading accounts
        accounts = await rest.get_accounts()
        for acc in accounts:
            print(f"{acc.account_id}: {acc.balance:.2f} {acc.currency} ({acc.account_type})")

        # Request OTP WebSocket trading URL
        otp_url = await rest.get_otp_url(accounts[0].account_id)
        print("WebSocket OTP URL:", otp_url)


asyncio.run(main())
```

---

## API reference

### `DerivAPI` — WebSocket (high-level)

| Method | Auth | Description |
|--------|------|-------------|
| `get_active_symbols(mode, contract_type)` | Optional | List active symbols (public or account-specific) |
| `get_contracts_for(symbol)` | Optional | Available contracts for a symbol |
| `get_contracts_list()` | No | All contract categories |
| `get_proposal(contract_type, currency, symbol, ...)` | Optional | One-shot or cached price quote |
| `stream_proposal(contract_type, currency, symbol, ...)` | Optional | Streaming price quotes |
| `stream_ticks(symbol)` | No | Real-time tick stream |
| `get_ticks_history(symbol, ...)` | No | Historic ticks or OHLC candles |
| `stream_ticks_history(symbol, ...)` | No | History + live candle/tick stream |
| `get_trading_times(date)` | No | Market opening/closing times |
| `get_server_time()` | No | Server epoch time |
| `ping()` | No | Keepalive / connectivity check |
| `get_balance()` | Yes (OTP/PAT) | Current account balance |
| `stream_balance()` | Yes (OTP/PAT) | Real-time balance updates |
| `buy(proposal_id, price)` | Yes (OTP/PAT) | Buy from a proposal ID |
| `buy_with_parameters(params, price)` | Yes (OTP/PAT) | Buy with inline parameters (auto-resolves proposal) |
| `stream_buy(proposal_id, price)` | Yes (OTP/PAT) | Buy and stream open-contract updates |
| `sell(contract_id, price)` | Yes (OTP/PAT) | Sell an open contract |
| `cancel(contract_id)` | Yes (OTP/PAT) | Cancel a contract (multipliers) |
| `get_portfolio(contract_type)` | Yes (OTP/PAT) | Open contract positions |
| `get_proposal_open_contract(contract_id)` | Yes (OTP/PAT) | Latest status for an open contract |
| `stream_proposal_open_contract(contract_id)` | Yes (OTP/PAT) | Live tick updates for an open contract |
| `update_contract(contract_id, ...)` | Yes (OTP/PAT) | Update stop-loss / take-profit |
| `get_contract_update_history(contract_id)` | Yes (OTP/PAT) | Contract update history |
| `get_statement(...)` | Yes (OTP/PAT) | Account transaction history |
| `get_profit_table(...)` | Yes (OTP/PAT) | Sold contracts profit/loss |
| `stream_transactions()` | Yes (OTP/PAT) | Real-time transaction stream |
| `forget(stream_id)` | No | Cancel a stream by ID |
| `forget_all(stream_types)` | No | Cancel all streams by type |
| `logout()` | Yes (OTP/PAT) | Log out the session |
| `send(payload)` | — | Raw request (escape hatch) |
| `subscribe(payload)` | — | Raw subscription (escape hatch) |

### `DerivRestClient` — REST HTTP

| Method | Auth | Description |
|--------|------|-------------|
| `health()` | No | API health check |
| `get_accounts()` | PAT / Bearer | List Options trading accounts |
| `get_otp_url(account_id)` | PAT / Bearer | Generate pre-authenticated WebSocket OTP URL |
| `create_account(account_type, currency, group)` | PAT / Bearer | Create an account |
| `get_legacy_accounts()` | PAT / Bearer | Legacy accounts grouped by login ID |
| `get_legacy_migration_status()` | PAT / Bearer | Platform upgrade status |

### `DerivClient` — WebSocket (low-level)

Direct access to the transport layer with automatic fallback and auto-OTP support.

```python
from deriv_api import DerivClient

async with DerivClient(token="YOUR_TOKEN") as client:
    response = await client.send({"ping": 1})
```

---

## Error handling

```python
from deriv_api import (
    DerivConnectionError,  # network / connection issues
    DerivAuthError,  # missing or invalid token
    DerivRequestError,  # API-level error (has .code, .message, .details)
    DerivTimeoutError,  # no response within timeout
)

try:
    balance = await api.get_balance()
except DerivAuthError as e:
    print(f"Not authorized: {e.message}")
except DerivRequestError as e:
    print(f"API error [{e.code}]: {e.message}")
```

---

## Environment variables

The library loads `.env` automatically on import. Application settings in your project take priority over library defaults.

| Variable | Description |
|----------|-------------|
| `DERIV_TOKEN` | Personal Access Token (PAT) for authenticated trading and REST |
| `DERIV_APP_ID` | Registered Deriv Application ID (default stored in `deriv_api/.env`) |
| `DERIV_ENDPOINT` | WebSocket endpoint (default: `wss://red.derivws.com/websockets/v3`) |

---

## Running the examples

All examples are verified and can be run as Python modules:

```bash
# 01 — Active symbols and contract types (public or authenticated)
python -m deriv_api.examples.01_active_symbols

# 02 — Check balance and buy a Rise/Fall contract (auto-OTP)
DERIV_TOKEN=your_token python -m deriv_api.examples.02_balance_and_buy

# 03 — Real-time live subscriptions (concurrent balance and tick stream)
DERIV_TOKEN=your_token python -m deriv_api.examples.03_subscriptions

# 04 — REST API: account listing and OTP URL generation
DERIV_TOKEN=your_token python -m deriv_api.examples.04_rest_accounts

# 05 — Full OTP WebSocket authentication workflow (step-by-step)
DERIV_TOKEN=your_token python -m deriv_api.examples.05_otp_websocket

# 06 — Complete trading lifecycle: Proposal → Buy → Live Contract Monitoring
DERIV_TOKEN=your_token python -m deriv_api.examples.06_proposal_and_trade_monitoring
```

---

## Project structure

```
deriv_api/
├── __init__.py        # Public API surface + auto .env loading
├── api.py             # High-level typed methods (DerivAPI)
├── client.py          # WebSocket transport & auto-OTP (DerivClient)
├── rest_client.py     # REST HTTP client (DerivRestClient)
├── models.py          # Request / response dataclasses
├── exceptions.py      # Exception hierarchy
├── setup_cli.py       # deriv-setup interactive wizard
└── examples/
    ├── 01_active_symbols.py
    ├── 02_balance_and_buy.py
    ├── 03_subscriptions.py
    ├── 04_rest_accounts.py
    ├── 05_otp_websocket.py
    └── 06_proposal_and_trade_monitoring.py
```

---

## License

MIT
