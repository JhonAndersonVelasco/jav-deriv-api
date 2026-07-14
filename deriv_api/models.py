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

    def to_dict(self) -> dict:
        d: dict = {}
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
    active_symbols: str = "brief"           # "full" | "brief"
    contract_type: list[str] | None = None
    passthrough: dict | None = None
    req_id: int | None = None

    def to_dict(self) -> dict:
        d: dict = {"active_symbols": self.active_symbols}
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
    symbol: str           # brief: "symbol",      full: "underlying_symbol"
    display_name: str     # brief: "display_name", full: "underlying_symbol_name"
    # Optional fields — present in brief
    pip: float | None = None             # brief: "pip",         full: "pip_size"
    subgroup: str | None = None
    submarket: str | None = None
    symbol_type: str | None = None       # brief: "symbol_type", full: "underlying_symbol_type"
    market_display_name: str | None = None
    subgroup_display_name: str | None = None
    submarket_display_name: str | None = None
    allow_forward_starting: int | None = None
    close_only: int | None = None
    display_order: int | None = None
    # Remaining / unknown fields land here
    extra: dict = field(default_factory=dict)

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
    def from_dict(cls, d: dict) -> "ActiveSymbol":
        known = {
            # brief keys
            "symbol", "display_name", "pip", "symbol_type",
            "market_display_name", "subgroup_display_name", "submarket_display_name",
            "allow_forward_starting", "close_only", "display_order",
            # full-mode aliases
            "underlying_symbol", "underlying_symbol_name", "pip_size",
            "underlying_symbol_type", "trade_count",
            # shared
            "exchange_is_open", "is_trading_suspended", "market",
            "subgroup", "submarket",
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
    passthrough: dict | None = None
    req_id: int | None = None

    def to_dict(self) -> dict:
        d: dict = {"balance": 1}
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
    def from_dict(cls, d: dict) -> "BalanceResponse":
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

    ``contract_type``, ``currency``, and ``underlying_symbol`` are required.
    """
    contract_type: str
    currency: str
    underlying_symbol: str
    amount: float | None = None
    barrier: str | None = None
    barrier2: str | None = None
    basis: str | None = None          # "payout" | "stake"
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

    def to_dict(self) -> dict:
        d: dict = {
            "contract_type": self.contract_type,
            "currency": self.currency,
            "underlying_symbol": self.underlying_symbol,
        }
        for attr in (
            "amount", "barrier", "barrier2", "basis", "cancellation",
            "date_expiry", "duration", "duration_unit", "growth_rate",
            "multiplier", "payout_per_point", "selected_tick",
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
    buy: str                        # proposal_id or "1"
    price: float                    # maximum acceptable price
    parameters: BuyParameters | None = None
    subscribe: bool = False         # stream contract updates after buy
    passthrough: dict | None = None
    req_id: int | None = None

    def to_dict(self) -> dict:
        d: dict = {"buy": self.buy, "price": self.price}
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
    def from_dict(cls, d: dict) -> "BuyResponse":
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
    passthrough: dict | None = None
    req_id: int | None = None

    def to_dict(self) -> dict:
        d: dict = {"cancel": self.contract_id}
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
    def from_dict(cls, d: dict) -> "CancelResponse":
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
# contracts_for
# ---------------------------------------------------------------------------

@dataclass
class ContractsForRequest:
    """
    Get available contracts for a given symbol.

    ``symbol`` is the short code from ``active_symbols`` (e.g. ``"R_50"``).
    """
    symbol: str
    passthrough: dict | None = None
    req_id: int | None = None

    def to_dict(self) -> dict:
        d: dict = {"contracts_for": self.symbol}
        if self.passthrough is not None:
            d["passthrough"] = self.passthrough
        if self.req_id is not None:
            d["req_id"] = self.req_id
        return d


# ---------------------------------------------------------------------------
# contracts_list
# ---------------------------------------------------------------------------

@dataclass
class ContractsListRequest:
    """Get the list of all contract categories on the platform."""
    passthrough: dict | None = None
    req_id: int | None = None

    def to_dict(self) -> dict:
        d: dict = {"contracts_list": 1}
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
    def from_dict(cls, d: dict) -> "ContractCategory":
        return cls(
            contract_category=d["contract_category"],
            contract_types=d["contract_types"],
            display_name=d["display_name"],
        )


# ---------------------------------------------------------------------------
# contract_update
# ---------------------------------------------------------------------------

@dataclass
class ContractUpdateRequest:
    """Update stop-loss or take-profit on an open contract. Requires trade scope."""
    contract_id: int
    limit_order: LimitOrder
    passthrough: dict | None = None
    req_id: int | None = None

    def to_dict(self) -> dict:
        d: dict = {
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
    passthrough: dict | None = None
    req_id: int | None = None

    def to_dict(self) -> dict:
        d: dict = {
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
    passthrough: dict | None = None
    req_id: int | None = None

    def to_dict(self) -> dict:
        d: dict = {"forget": self.stream_id}
        if self.passthrough is not None:
            d["passthrough"] = self.passthrough
        if self.req_id is not None:
            d["req_id"] = self.req_id
        return d


STREAM_TYPES = (
    "balance", "candles", "cashier_payments", "proposal",
    "proposal_open_contract", "ticks", "transaction",
)


@dataclass
class ForgetAllRequest:
    """
    Cancel all active streams of one or more types.

    ``stream_types`` accepts a single string or a list, e.g.
    ``"ticks"`` or ``["ticks", "balance"]``.
    """
    stream_types: str | list[str]
    passthrough: dict | None = None
    req_id: int | None = None

    def to_dict(self) -> dict:
        d: dict = {"forget_all": self.stream_types}
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
    status: str       # "active" | "inactive"
    account_type: str  # "demo" | "real"
    created_at: str | None = None
    email: str | None = None
    last_access_at: str | None = None
    name: str | None = None
    server_id: str | None = None
    rights: dict = field(default_factory=dict)

    @classmethod
    def from_dict(cls, d: dict) -> "AccountInfo":
        return cls(
            account_id=d["account_id"],
            balance=d["balance"],
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
    account_type: str = "demo"   # "demo" | "real"

    def to_dict(self) -> dict:
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
    def from_dict(cls, d: dict) -> "LegacyAccount":
        return cls(account_id=d["account_id"], currency=d["currency"])
