"""
Data models (dataclasses) for Deriv API requests and responses.

All models are plain dataclasses for easy construction and inspection.
Optional fields default to None so callers only need to pass what they need.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

# ---------------------------------------------------------------------------
# Shared / common
# ---------------------------------------------------------------------------


@dataclass
class LimitOrder:
    """Stop-loss / take-profit order attached to a contract."""

    stop_loss: float | None = None
    take_profit: float | None = None

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {}
        if self.stop_loss is not None:
            d["stop_loss"] = self.stop_loss
        if self.take_profit is not None:
            d["take_profit"] = self.take_profit
        return d


# ---------------------------------------------------------------------------
# active_symbols
# ---------------------------------------------------------------------------


@dataclass
class ActiveSymbolsRequest:
    """
    Retrieve a list of all currently active symbols.

    Args:
        active_symbols: ``"full"`` for all fields, ``"brief"`` for a subset.
        contract_type: Optional filter by contract type(s).
        passthrough: Arbitrary data echoed back in the response.
        req_id: Optional integer to correlate request with response.
    """

    active_symbols: str = "brief"  # "full" | "brief"
    contract_type: list[str] | None = None
    passthrough: dict[str, Any] | None = None
    req_id: int | None = None

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {"active_symbols": self.active_symbols}
        if self.contract_type is not None:
            d["contract_type"] = self.contract_type
        if self.passthrough is not None:
            d["passthrough"] = self.passthrough
        if self.req_id is not None:
            d["req_id"] = self.req_id
        return d


@dataclass
class ActiveSymbol:
    # Core fields — present in both "brief" and "full" responses
    exchange_is_open: int
    is_trading_suspended: int
    market: str
    symbol: str  # brief: "symbol",      full: "underlying_symbol"
    display_name: str  # brief: "display_name", full: "underlying_symbol_name"
    # Optional fields — present in brief
    pip: float | None = None  # brief: "pip",         full: "pip_size"
    subgroup: str | None = None
    submarket: str | None = None
    symbol_type: str | None = None  # brief: "symbol_type", full: "underlying_symbol_type"
    market_display_name: str | None = None
    subgroup_display_name: str | None = None
    submarket_display_name: str | None = None
    allow_forward_starting: int | None = None
    close_only: int | None = None
    display_order: int | None = None
    # Remaining / unknown fields land here
    extra: dict[str, Any] = field(default_factory=dict)

    # Convenience aliases so existing code using the old names keeps working
    @property
    def underlying_symbol(self) -> str:
        return self.symbol

    @property
    def underlying_symbol_name(self) -> str:
        return self.display_name

    @property
    def pip_size(self) -> float | None:
        return self.pip

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> ActiveSymbol:
        known = {
            # brief keys
            "symbol",
            "display_name",
            "pip",
            "symbol_type",
            "market_display_name",
            "subgroup_display_name",
            "submarket_display_name",
            "allow_forward_starting",
            "close_only",
            "display_order",
            # full-mode aliases
            "underlying_symbol",
            "underlying_symbol_name",
            "pip_size",
            "underlying_symbol_type",
            "trade_count",
            # shared
            "exchange_is_open",
            "is_trading_suspended",
            "market",
            "subgroup",
            "submarket",
        }
        return cls(
            exchange_is_open=d["exchange_is_open"],
            is_trading_suspended=d["is_trading_suspended"],
            market=d["market"],
            # Normalise: prefer brief key, fall back to full-mode key
            symbol=d.get("symbol") or d.get("underlying_symbol", ""),
            display_name=d.get("display_name") or d.get("underlying_symbol_name", ""),
            pip=d.get("pip") or d.get("pip_size"),
            subgroup=d.get("subgroup"),
            submarket=d.get("submarket"),
            symbol_type=d.get("symbol_type") or d.get("underlying_symbol_type"),
            market_display_name=d.get("market_display_name"),
            subgroup_display_name=d.get("subgroup_display_name"),
            submarket_display_name=d.get("submarket_display_name"),
            allow_forward_starting=d.get("allow_forward_starting"),
            close_only=d.get("close_only"),
            display_order=d.get("display_order"),
            extra={k: v for k, v in d.items() if k not in known},
        )


# ---------------------------------------------------------------------------
# balance
# ---------------------------------------------------------------------------


@dataclass
class BalanceRequest:
    """
    Get the account balance, optionally subscribing to live updates.

    Requires authentication (trade scope).
    """

    subscribe: bool = False
    passthrough: dict[str, Any] | None = None
    req_id: int | None = None

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {"balance": 1}
        if self.subscribe:
            d["subscribe"] = 1
        if self.passthrough is not None:
            d["passthrough"] = self.passthrough
        if self.req_id is not None:
            d["req_id"] = self.req_id
        return d


@dataclass
class BalanceResponse:
    balance: float
    currency: str
    loginid: str
    subscription_id: str | None = None
    req_id: int | None = None

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> BalanceResponse:
        b = d["balance"]
        sub = d.get("subscription", {})
        return cls(
            balance=b["balance"],
            currency=b["currency"],
            loginid=b["loginid"],
            subscription_id=sub.get("id"),
            req_id=d.get("req_id"),
        )


# ---------------------------------------------------------------------------
# buy
# ---------------------------------------------------------------------------


@dataclass
class BuyParameters:
    """
    Parameters for buying a contract directly (without a prior proposal).

    ``contract_type``, ``currency``, and ``symbol`` are required.
    Note: the API field name is ``symbol`` (not ``underlying_symbol``).
    """

    contract_type: str
    currency: str
    symbol: str
    amount: float | None = None
    barrier: str | None = None
    barrier2: str | None = None
    basis: str | None = None  # "payout" | "stake"
    cancellation: str | None = None
    date_expiry: int | None = None
    duration: int | None = None
    duration_unit: str | None = None  # "s" | "m" | "h" | "d" | "t"
    growth_rate: float | None = None
    limit_order: LimitOrder | None = None
    multiplier: float | None = None
    payout_per_point: float | None = None
    selected_tick: int | None = None
    app_markup_percentage: float | None = None

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {
            "contract_type": self.contract_type,
            "currency": self.currency,
            "symbol": self.symbol,
        }
        for attr in (
            "amount",
            "barrier",
            "barrier2",
            "basis",
            "cancellation",
            "date_expiry",
            "duration",
            "duration_unit",
            "growth_rate",
            "multiplier",
            "payout_per_point",
            "selected_tick",
            "app_markup_percentage",
        ):
            v = getattr(self, attr)
            if v is not None:
                d[attr] = v
        if self.limit_order is not None:
            d["limit_order"] = self.limit_order.to_dict()
        return d


@dataclass
class BuyRequest:
    """
    Buy a contract.

    ``buy`` is either a proposal ID string or ``"1"`` when passing
    ``parameters`` directly.
    """

    buy: str  # proposal_id or "1"
    price: float  # maximum acceptable price
    parameters: BuyParameters | None = None
    subscribe: bool = False  # stream contract updates after buy
    passthrough: dict[str, Any] | None = None
    req_id: int | None = None

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {"buy": self.buy, "price": self.price}
        if self.parameters is not None:
            d["parameters"] = self.parameters.to_dict()
        if self.subscribe:
            d["subscribe"] = 1
        if self.passthrough is not None:
            d["passthrough"] = self.passthrough
        if self.req_id is not None:
            d["req_id"] = self.req_id
        return d


@dataclass
class BuyResponse:
    balance_after: float
    buy_price: float
    contract_id: int
    longcode: str
    payout: float
    purchase_time: int
    shortcode: str
    start_time: int
    transaction_id: int
    subscription_id: str | None = None
    req_id: int | None = None

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> BuyResponse:
        b = d["buy"]
        sub = d.get("subscription", {})
        return cls(
            balance_after=b["balance_after"],
            buy_price=b["buy_price"],
            contract_id=b["contract_id"],
            longcode=b["longcode"],
            payout=b["payout"],
            purchase_time=b["purchase_time"],
            shortcode=b["shortcode"],
            start_time=b["start_time"],
            transaction_id=b["transaction_id"],
            subscription_id=sub.get("id"),
            req_id=d.get("req_id"),
        )


# ---------------------------------------------------------------------------
# cancel
# ---------------------------------------------------------------------------


@dataclass
class CancelRequest:
    """Cancel a contract by its contract_id. Requires trade scope."""

    contract_id: int
    passthrough: dict[str, Any] | None = None
    req_id: int | None = None

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {"cancel": self.contract_id}
        if self.passthrough is not None:
            d["passthrough"] = self.passthrough
        if self.req_id is not None:
            d["req_id"] = self.req_id
        return d


@dataclass
class CancelResponse:
    balance_after: float | None = None
    contract_id: int | None = None
    reference_id: int | None = None
    sold_for: float | None = None
    transaction_id: int | None = None
    req_id: int | None = None

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> CancelResponse:
        c = d.get("cancel", {})
        return cls(
            balance_after=c.get("balance_after"),
            contract_id=c.get("contract_id"),
            reference_id=c.get("reference_id"),
            sold_for=c.get("sold_for"),
            transaction_id=c.get("transaction_id"),
            req_id=d.get("req_id"),
        )


# ---------------------------------------------------------------------------
# contracts_list
# ---------------------------------------------------------------------------


@dataclass
class ContractsListRequest:
    """Get all contract categories available on the platform. No auth required."""

    passthrough: dict[str, Any] | None = None
    req_id: int | None = None

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {"contracts_list": 1}
        if self.passthrough is not None:
            d["passthrough"] = self.passthrough
        if self.req_id is not None:
            d["req_id"] = self.req_id
        return d


@dataclass
class ContractCategory:
    contract_category: str
    contract_types: list[str]
    display_name: str

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> ContractCategory:
        return cls(
            contract_category=d["contract_category"],
            contract_types=d["contract_types"],
            display_name=d["display_name"],
        )


# ---------------------------------------------------------------------------
# proposal_open_contract
# ---------------------------------------------------------------------------


@dataclass
class ProposalOpenContractRequest:
    """
    Get the latest price and details for open contract(s) in the portfolio.

    If ``contract_id`` is omitted, streams updates for all open contracts.
    Requires trade scope.
    """

    contract_id: int | None = None
    subscribe: bool = False
    passthrough: dict[str, Any] | None = None
    req_id: int | None = None

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {"proposal_open_contract": 1}
        if self.contract_id is not None:
            d["contract_id"] = self.contract_id
        if self.subscribe:
            d["subscribe"] = 1
        if self.passthrough is not None:
            d["passthrough"] = self.passthrough
        if self.req_id is not None:
            d["req_id"] = self.req_id
        return d


# ---------------------------------------------------------------------------
# logout
# ---------------------------------------------------------------------------


@dataclass
class LogoutRequest:
    """Logout the current session. Requires trade scope."""

    passthrough: dict[str, Any] | None = None
    req_id: int | None = None

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {"logout": 1}
        if self.passthrough is not None:
            d["passthrough"] = self.passthrough
        if self.req_id is not None:
            d["req_id"] = self.req_id
        return d


# ---------------------------------------------------------------------------
# contracts_for
# ---------------------------------------------------------------------------


@dataclass
class ContractsForRequest:
    """
    Get available contracts for a given symbol.

    ``symbol`` is the short code from ``active_symbols`` (e.g. ``"R_50"``).
    """

    symbol: str
    passthrough: dict[str, Any] | None = None
    req_id: int | None = None

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {"contracts_for": self.symbol}
        if self.passthrough is not None:
            d["passthrough"] = self.passthrough
        if self.req_id is not None:
            d["req_id"] = self.req_id
        return d


# ---------------------------------------------------------------------------
# contract_update
# ---------------------------------------------------------------------------


@dataclass
class ContractUpdateRequest:
    """Update stop-loss or take-profit on an open contract. Requires trade scope."""

    contract_id: int
    limit_order: LimitOrder
    passthrough: dict[str, Any] | None = None
    req_id: int | None = None

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {
            "contract_update": 1,
            "contract_id": self.contract_id,
            "limit_order": self.limit_order.to_dict(),
        }
        if self.passthrough is not None:
            d["passthrough"] = self.passthrough
        if self.req_id is not None:
            d["req_id"] = self.req_id
        return d


# ---------------------------------------------------------------------------
# contract_update_history
# ---------------------------------------------------------------------------


@dataclass
class ContractUpdateHistoryRequest:
    """Get the update history of a contract. Requires trade scope."""

    contract_id: int
    limit: int = 500
    passthrough: dict[str, Any] | None = None
    req_id: int | None = None

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {
            "contract_update_history": 1,
            "contract_id": self.contract_id,
            "limit": self.limit,
        }
        if self.passthrough is not None:
            d["passthrough"] = self.passthrough
        if self.req_id is not None:
            d["req_id"] = self.req_id
        return d


# ---------------------------------------------------------------------------
# forget / forget_all
# ---------------------------------------------------------------------------


@dataclass
class ForgetRequest:
    """Cancel a specific real-time stream by its subscription ID."""

    stream_id: str
    passthrough: dict[str, Any] | None = None
    req_id: int | None = None

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {"forget": self.stream_id}
        if self.passthrough is not None:
            d["passthrough"] = self.passthrough
        if self.req_id is not None:
            d["req_id"] = self.req_id
        return d


STREAM_TYPES = (
    "balance",
    "candles",
    "cashier_payments",
    "proposal",
    "proposal_open_contract",
    "ticks",
    "transaction",
)


@dataclass
class ForgetAllRequest:
    """
    Cancel all active streams of one or more types.

    ``stream_types`` accepts a single string or a list, e.g.
    ``"ticks"`` or ``["ticks", "balance"]``.
    """

    stream_types: str | list[str]
    passthrough: dict[str, Any] | None = None
    req_id: int | None = None

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {"forget_all": self.stream_types}
        if self.passthrough is not None:
            d["passthrough"] = self.passthrough
        if self.req_id is not None:
            d["req_id"] = self.req_id
        return d


# ---------------------------------------------------------------------------
# REST: account models
# ---------------------------------------------------------------------------


@dataclass
class AccountInfo:
    account_id: str
    balance: float
    currency: str
    group: str
    status: str  # "active" | "inactive"
    account_type: str  # "demo" | "real"
    created_at: str | None = None
    email: str | None = None
    last_access_at: str | None = None
    name: str | None = None
    server_id: str | None = None
    rights: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> AccountInfo:
        return cls(
            account_id=d["account_id"],
            balance=float(d["balance"]) if d.get("balance") is not None else 0.0,
            currency=d["currency"],
            group=d["group"],
            status=d["status"],
            account_type=d["account_type"],
            created_at=d.get("created_at"),
            email=d.get("email"),
            last_access_at=d.get("last_access_at"),
            name=d.get("name"),
            server_id=d.get("server_id"),
            rights=d.get("rights", {}),
        )


@dataclass
class CreateAccountRequest:
    """Request body for creating a new Options trading account via REST."""

    currency: str = "USD"
    group: str = "row"
    account_type: str = "demo"  # "demo" | "real"

    def to_dict(self) -> dict[str, Any]:
        return {
            "currency": self.currency,
            "group": self.group,
            "account_type": self.account_type,
        }


@dataclass
class LegacyAccount:
    account_id: int
    currency: str

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> LegacyAccount:
        return cls(account_id=d["account_id"], currency=d["currency"])


# ---------------------------------------------------------------------------
# proposal
# ---------------------------------------------------------------------------


@dataclass
class ProposalRequest:
    """
    Get a price proposal for a contract.

    ``contract_type``, ``currency``, and ``underlying_symbol`` are required.
    Either ``duration`` or ``date_expiry`` must be provided.
    """

    contract_type: str
    currency: str
    underlying_symbol: str
    amount: float | None = None
    barrier: str | None = None
    barrier2: str | None = None
    basis: str | None = None  # "payout" | "stake"
    cancellation: str | None = None
    date_expiry: int | None = None
    duration: int | None = None
    duration_unit: str | None = None  # "s" | "m" | "h" | "d" | "t"
    growth_rate: float | None = None
    limit_order: LimitOrder | None = None
    multiplier: float | None = None
    payout_per_point: float | None = None
    selected_tick: int | None = None
    subscribe: bool = False
    passthrough: dict[str, Any] | None = None
    req_id: int | None = None

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {
            "proposal": 1,
            "contract_type": self.contract_type,
            "currency": self.currency,
            "underlying_symbol": self.underlying_symbol,
        }
        for attr in (
            "amount",
            "barrier",
            "barrier2",
            "basis",
            "cancellation",
            "date_expiry",
            "duration",
            "duration_unit",
            "growth_rate",
            "multiplier",
            "payout_per_point",
            "selected_tick",
        ):
            v = getattr(self, attr)
            if v is not None:
                d[attr] = v
        if self.subscribe:
            d["subscribe"] = 1
        if self.limit_order is not None:
            d["limit_order"] = self.limit_order.to_dict()
        if self.passthrough is not None:
            d["passthrough"] = self.passthrough
        if self.req_id is not None:
            d["req_id"] = self.req_id
        return d


@dataclass
class ProposalResponse:
    id: str  # proposal ID — pass to buy()
    ask_price: float
    payout: float
    spot: float
    spot_time: int
    date_start: int
    longcode: str
    date_expiry: int | None = None
    commission: float | None = None
    multiplier: float | None = None
    min_stake: float | None = None
    max_stake: float | None = None
    subscription_id: str | None = None
    extra: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> ProposalResponse:
        p = d.get("proposal", d)  # tolerate both raw and wrapped
        known = {
            "id",
            "ask_price",
            "payout",
            "spot",
            "spot_time",
            "date_start",
            "longcode",
            "date_expiry",
            "commission",
            "multiplier",
            "min_stake",
            "max_stake",
        }
        sub = d.get("subscription", {})
        return cls(
            id=p["id"],
            ask_price=p["ask_price"],
            payout=p["payout"],
            spot=p["spot"],
            spot_time=p["spot_time"],
            date_start=p["date_start"],
            longcode=p["longcode"],
            date_expiry=p.get("date_expiry"),
            commission=p.get("commission"),
            multiplier=p.get("multiplier"),
            min_stake=p.get("min_stake"),
            max_stake=p.get("max_stake"),
            subscription_id=sub.get("id") if sub else None,
            extra={k: v for k, v in p.items() if k not in known},
        )


# ---------------------------------------------------------------------------
# sell
# ---------------------------------------------------------------------------


@dataclass
class SellRequest:
    """Sell an open contract at market or at a minimum price."""

    contract_id: int
    price: float = 0.0  # 0 = sell at market
    passthrough: dict[str, Any] | None = None
    req_id: int | None = None

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {"sell": self.contract_id, "price": self.price}
        if self.passthrough is not None:
            d["passthrough"] = self.passthrough
        if self.req_id is not None:
            d["req_id"] = self.req_id
        return d


@dataclass
class SellResponse:
    balance_after: float | None = None
    contract_id: int | None = None
    reference_id: int | None = None
    sold_for: float | None = None
    transaction_id: int | None = None
    req_id: int | None = None

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> SellResponse:
        s = d.get("sell", {})
        return cls(
            balance_after=s.get("balance_after"),
            contract_id=s.get("contract_id"),
            reference_id=s.get("reference_id"),
            sold_for=s.get("sold_for"),
            transaction_id=s.get("transaction_id"),
            req_id=d.get("req_id"),
        )


# ---------------------------------------------------------------------------
# ticks / ticks_history
# ---------------------------------------------------------------------------


@dataclass
class TicksRequest:
    """Subscribe to real-time tick stream for one or more symbols."""

    ticks: str | list[str]
    subscribe: bool = True
    passthrough: dict[str, Any] | None = None
    req_id: int | None = None

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {"ticks": self.ticks}
        if self.subscribe:
            d["subscribe"] = 1
        if self.passthrough is not None:
            d["passthrough"] = self.passthrough
        if self.req_id is not None:
            d["req_id"] = self.req_id
        return d


@dataclass
class Tick:
    symbol: str
    epoch: int
    quote: float
    ask: float | None = None
    bid: float | None = None
    pip_size: float | None = None
    subscription_id: str | None = None

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> Tick:
        t = d.get("tick", d)
        sub = d.get("subscription", {})
        return cls(
            symbol=t.get("symbol", ""),
            epoch=t.get("epoch", 0),
            quote=t.get("quote", 0.0),
            ask=t.get("ask"),
            bid=t.get("bid"),
            pip_size=t.get("pip_size"),
            subscription_id=sub.get("id") if sub else None,
        )


@dataclass
class TicksHistoryRequest:
    """
    Get historic tick data or OHLC candles for a symbol.

    ``end`` is required; use ``"latest"`` for the most recent data.
    """

    ticks_history: str
    end: str = "latest"  # epoch string or "latest"
    start: int | None = None
    count: int | None = None
    style: str = "ticks"  # "ticks" | "candles"
    granularity: int | None = None  # candle width in seconds
    adjust_start_time: bool = False
    subscribe: bool = False
    passthrough: dict[str, Any] | None = None
    req_id: int | None = None

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {
            "ticks_history": self.ticks_history,
            "end": self.end,
            "style": self.style,
        }
        if self.start is not None:
            d["start"] = self.start
        if self.count is not None:
            d["count"] = self.count
        if self.granularity is not None:
            d["granularity"] = self.granularity
        if self.adjust_start_time:
            d["adjust_start_time"] = 1
        if self.subscribe:
            d["subscribe"] = 1
        if self.passthrough is not None:
            d["passthrough"] = self.passthrough
        if self.req_id is not None:
            d["req_id"] = self.req_id
        return d


# ---------------------------------------------------------------------------
# portfolio
# ---------------------------------------------------------------------------


@dataclass
class PortfolioRequest:
    """Get currently open contract positions. Requires trade scope."""

    contract_type: list[str] | None = None
    passthrough: dict[str, Any] | None = None
    req_id: int | None = None

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {"portfolio": 1}
        if self.contract_type is not None:
            d["contract_type"] = self.contract_type
        if self.passthrough is not None:
            d["passthrough"] = self.passthrough
        if self.req_id is not None:
            d["req_id"] = self.req_id
        return d


# ---------------------------------------------------------------------------
# profit_table
# ---------------------------------------------------------------------------


@dataclass
class ProfitTableRequest:
    """Get a list of sold contracts and their profit/loss. Requires trade scope."""

    limit: int = 100
    offset: int = 0
    date_from: int | str | None = None  # epoch integer/string or "YYYY-MM-DD"
    date_to: int | str | None = None  # epoch integer/string or "YYYY-MM-DD"
    description: bool = False
    sort: str = "DESC"  # "ASC" | "DESC"
    contract_type: list[str] | None = None
    passthrough: dict[str, Any] | None = None
    req_id: int | None = None

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {
            "profit_table": 1,
            "limit": self.limit,
            "offset": self.offset,
            "sort": self.sort,
        }
        if self.date_from is not None:
            d["date_from"] = self.date_from
        if self.date_to is not None:
            d["date_to"] = self.date_to
        if self.description:
            d["description"] = 1
        if self.contract_type is not None:
            d["contract_type"] = self.contract_type
        if self.passthrough is not None:
            d["passthrough"] = self.passthrough
        if self.req_id is not None:
            d["req_id"] = self.req_id
        return d


# ---------------------------------------------------------------------------
# statement
# ---------------------------------------------------------------------------


@dataclass
class StatementRequest:
    """Get account transaction history. Requires trade scope."""

    limit: int = 100
    offset: int = 0
    date_from: int | None = None
    date_to: int | None = None
    action_type: str | None = None  # "buy" | "sell" | "deposit" | "withdrawal"
    description: bool = False
    passthrough: dict[str, Any] | None = None
    req_id: int | None = None

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {
            "statement": 1,
            "limit": self.limit,
            "offset": self.offset,
        }
        if self.date_from is not None:
            d["date_from"] = self.date_from
        if self.date_to is not None:
            d["date_to"] = self.date_to
        if self.action_type is not None:
            d["action_type"] = self.action_type
        if self.description:
            d["description"] = 1
        if self.passthrough is not None:
            d["passthrough"] = self.passthrough
        if self.req_id is not None:
            d["req_id"] = self.req_id
        return d


# ---------------------------------------------------------------------------
# transaction (subscription)
# ---------------------------------------------------------------------------


@dataclass
class TransactionRequest:
    """Subscribe to real-time transaction updates. Requires trade scope."""

    subscribe: bool = True
    passthrough: dict[str, Any] | None = None
    req_id: int | None = None

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {"transaction": 1, "subscribe": 1 if self.subscribe else 0}
        if self.passthrough is not None:
            d["passthrough"] = self.passthrough
        if self.req_id is not None:
            d["req_id"] = self.req_id
        return d


# ---------------------------------------------------------------------------
# ping / time / trading_times
# ---------------------------------------------------------------------------


@dataclass
class PingRequest:
    passthrough: dict[str, Any] | None = None
    req_id: int | None = None

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {"ping": 1}
        if self.passthrough is not None:
            d["passthrough"] = self.passthrough
        if self.req_id is not None:
            d["req_id"] = self.req_id
        return d


@dataclass
class TimeRequest:
    passthrough: dict[str, Any] | None = None
    req_id: int | None = None

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {"time": 1}
        if self.passthrough is not None:
            d["passthrough"] = self.passthrough
        if self.req_id is not None:
            d["req_id"] = self.req_id
        return d


@dataclass
class TradingTimesRequest:
    trading_times: str  # date string "yyyy-mm-dd" or "today"
    passthrough: dict[str, Any] | None = None
    req_id: int | None = None

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {"trading_times": self.trading_times}
        if self.passthrough is not None:
            d["passthrough"] = self.passthrough
        if self.req_id is not None:
            d["req_id"] = self.req_id
        return d
