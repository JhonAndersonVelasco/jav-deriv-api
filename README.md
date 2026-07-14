# jav-deriv-api-python

Async Python client library for the [Deriv](https://deriv.com) trading API.

Covers the full WebSocket API (real-time prices, trading, subscriptions) and
the REST HTTP API (account management). Built on top of `websockets` and
`aiohttp`. Requires Python ≥ 3.10.

---

## Installation

```bash
pip install deriv-api
```

After installation, run the interactive setup wizard to create your `.env` file:

```bash
deriv-setup
```

This will prompt for your [Deriv API token](https://app.deriv.com/account/api-token)
and save it to `.env` automatically.

---

## Quick start

### Active symbols (no auth needed)

```python
import asyncio
from jav_deriv_api import DerivAPI

async def main():
    async with DerivAPI(app_id=1089) as api:
        symbols = await api.get_active_symbols(mode="brief")
        for s in symbols:
            print(s.symbol, s.display_name)

asyncio.run(main())
```

### Balance and buy a contract

```python
import asyncio
from jav_deriv_api import DerivAPI, BuyParameters

async def main():
    async with DerivAPI(app_id=1089, token="YOUR_TOKEN") as api:
        balance = await api.get_balance()
        print(f"{balance.balance:.2f} {balance.currency}")

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
        print(f"Contract {receipt.contract_id} bought for {receipt.buy_price}")

asyncio.run(main())
```

### Price proposal

```python
async with DerivAPI(app_id=1089) as api:
    proposal = await api.get_proposal(
        "CALL", "USD", "R_50",
        amount=1.0, basis="stake", duration=5, duration_unit="t"
    )
    print(f"Ask price: {proposal.ask_price}  ID: {proposal.id}")
    # Pass proposal.id to api.buy() to execute
```

### Real-time subscriptions

```python
import asyncio
from jav_deriv_api import DerivAPI

async def main():
    async with DerivAPI(app_id=1089, token="YOUR_TOKEN") as api:
        # Tick stream
        async for tick in api.stream_ticks("R_50"):
            print(tick.quote, tick.epoch)
            await api.forget(tick.subscription_id)
            break

        # Balance stream
        async for update in api.stream_balance():
            print(f"Balance: {update.balance} {update.currency}")
            await api.forget(update.subscription_id)
            break

asyncio.run(main())
```

### OHLC candles history

```python
async with DerivAPI(app_id=1089) as api:
    resp = await api.get_ticks_history(
        "R_50", style="candles", granularity=60, count=10
    )
    for candle in resp.get("candles", []):
        print(candle["epoch"], candle["open"], candle["close"])
```

### REST API — account management

> The REST API requires an **OAuth2 Bearer token**, which is different from
> the Personal Access Token used for WebSocket auth. See
> [Authentication docs](https://developers.deriv.com/llms/authentication.md).

```python
import asyncio
from jav_deriv_api import DerivRestClient

async def main():
    async with DerivRestClient(app_id="1089", token="OAUTH2_TOKEN") as rest:
        ok = await rest.health()
        print("API healthy:", ok)

        accounts = await rest.get_accounts()
        for acc in accounts:
            print(acc.account_id, acc.balance, acc.currency)

asyncio.run(main())
```

---

## API reference

### `DerivAPI` — WebSocket (high-level)

| Method | Auth | Description |
|--------|------|-------------|
| `get_active_symbols(mode, contract_type)` | No | List active symbols |
| `get_contracts_for(symbol)` | No | Available contracts for a symbol |
| `get_contracts_list()` | No | All contract categories |
| `get_proposal(contract_type, currency, symbol, ...)` | No | One-shot price quote |
| `stream_proposal(contract_type, currency, symbol, ...)` | No | Streaming price quotes |
| `stream_ticks(symbol)` | No | Real-time tick stream |
| `get_ticks_history(symbol, ...)` | No | Historic ticks or OHLC candles |
| `stream_ticks_history(symbol, ...)` | No | History + live candle/tick stream |
| `get_trading_times(date)` | No | Market opening/closing times |
| `get_server_time()` | No | Server epoch time |
| `ping()` | No | Keepalive / connectivity check |
| `get_balance()` | Yes | Current account balance |
| `stream_balance()` | Yes | Real-time balance updates |
| `buy(proposal_id, price)` | Yes | Buy from a proposal ID |
| `buy_with_parameters(params, price)` | Yes | Buy with inline `BuyParameters` |
| `stream_buy(proposal_id, price)` | Yes | Buy and stream open-contract updates |
| `sell(contract_id, price)` | Yes | Sell an open contract |
| `cancel(contract_id)` | Yes | Cancel a contract (multipliers) |
| `get_portfolio(contract_type)` | Yes | Open contract positions |
| `get_proposal_open_contract(contract_id)` | Yes | Latest price for an open contract |
| `stream_proposal_open_contract(contract_id)` | Yes | Live updates for an open contract |
| `update_contract(contract_id, ...)` | Yes | Update stop-loss / take-profit |
| `get_contract_update_history(contract_id)` | Yes | Contract update history |
| `get_statement(...)` | Yes | Account transaction history |
| `get_profit_table(...)` | Yes | Sold contracts profit/loss |
| `stream_transactions()` | Yes | Real-time transaction stream |
| `forget(stream_id)` | No | Cancel a stream by ID |
| `forget_all(stream_types)` | No | Cancel all streams by type |
| `logout()` | Yes | Log out the session |
| `send(payload)` | — | Raw request (escape hatch) |
| `subscribe(payload)` | — | Raw subscription (escape hatch) |

### `DerivRestClient` — REST HTTP

| Method | Auth | Description |
|--------|------|-------------|
| `health()` | No | API health check |
| `get_accounts()` | OAuth2 | List Options trading accounts |
| `create_account(account_type, currency, group)` | OAuth2 | Create an account |
| `get_legacy_accounts()` | OAuth2 | Legacy accounts grouped by login ID |
| `get_legacy_migration_status()` | OAuth2 | Platform upgrade status |

### `DerivClient` — WebSocket (low-level)

Direct access to the transport layer for endpoints not yet covered by `DerivAPI`.

```python
from jav_deriv_api import DerivClient

async with DerivClient(app_id=1089) as client:
    await client.authorize("YOUR_TOKEN")
    resp = await client.send({"ticks_history": "R_50", "end": "latest", "count": 5})
```

---

## Error handling

```python
from jav_deriv_api import (
    DerivConnectionError,  # network / connection issues
    DerivAuthError,        # missing or invalid token
    DerivRequestError,     # API-level error (has .code and .message)
    DerivTimeoutError,     # no response within timeout
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

The library loads `.env` automatically on import. Run `deriv-setup` after
installation to create it interactively.

| Variable | Description |
|----------|-------------|
| `DERIV_TOKEN` | Personal Access Token for WebSocket auth |
| `DERIV_OAUTH_TOKEN` | OAuth2 Bearer token for REST API |
| `DERIV_APP_ID` | Your application ID (default: `1089` demo) |
| `DERIV_ENDPOINT` | WebSocket endpoint (default: production) |

---

## Running the examples

```bash
# No auth needed
python deriv_api/examples/01_active_symbols.py

# Auth required — token is read from .env automatically
python deriv_api/examples/02_balance_and_buy.py
python deriv_api/examples/03_subscriptions.py

# REST API — requires OAuth2 token
python deriv_api/examples/04_rest_accounts.py
```

---

## Project structure

```
deriv_api/
├── __init__.py        # Public API surface + auto .env loading
├── api.py             # High-level typed methods (DerivAPI)
├── client.py          # Low-level WebSocket transport (DerivClient)
├── rest_client.py     # REST HTTP client (DerivRestClient)
├── models.py          # Request / response dataclasses
├── exceptions.py      # Exception hierarchy
├── setup_cli.py       # deriv-setup interactive wizard
└── examples/
    ├── 01_active_symbols.py
    ├── 02_balance_and_buy.py
    ├── 03_subscriptions.py
    └── 04_rest_accounts.py
```

---

## License

MIT
