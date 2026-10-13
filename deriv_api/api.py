"""
High-level WebSocket API methods for the Deriv API.

``DerivAPI`` wraps ``DerivClient`` and exposes every WebSocket endpoint as a
typed, documented Python method.  All methods return typed dataclass instances
or raw dicts for endpoints whose responses are naturally open-ended.

Subscription methods return async generators; call ``client.forget_stream()``
or use the ``forget`` / ``forget_all`` helpers to stop them.

Usage
-----
::

    from jav_deriv_api import DerivAPI

    async with DerivAPI(app_id=1234, token="YOUR_TOKEN") as api:
        symbols = await api.get_active_symbols()
        for s in symbols:
            print(s.underlying_symbol, s.underlying_symbol_name)

        # Subscribe to balance updates
        async for update in api.stream_balance():
            print(update.balance, update.currency)
            break  # stop after first update
"""

from __future__ import annotations

from collections.abc import AsyncGenerator
from types import TracebackType
from typing import Any, cast

from .client import DerivClient
from .exceptions import DerivRequestError
from .models import (
    ActiveSymbol,
    ActiveSymbolsRequest,
    BalanceRequest,
    BalanceResponse,
    BuyParameters,
    BuyRequest,
    BuyResponse,
    CancelRequest,
    CancelResponse,
    ContractCategory,
    ContractsForRequest,
    ContractsListRequest,
    ContractUpdateHistoryRequest,
    ContractUpdateRequest,
    ForgetAllRequest,
    LimitOrder,
    LogoutRequest,
    PingRequest,
    PortfolioRequest,
    ProfitTableRequest,
    ProposalOpenContractRequest,
    ProposalRequest,
    ProposalResponse,
    SellRequest,
    SellResponse,
    StatementRequest,
    Tick,
    TicksHistoryRequest,
    TicksRequest,
    TimeRequest,
    TradingTimesRequest,
    TransactionRequest,
)


class DerivAPI:
    """
    High-level async API client for Deriv's WebSocket API.

    Parameters
    ----------
    app_id:
        Your Deriv application ID.
    token:
        Optional API token — authorizes the session automatically on connect.
    **kwargs:
        Additional keyword arguments forwarded to ``DerivClient``
        (e.g. ``endpoint``, ``request_timeout``, ``reconnect``).
    """

    def __init__(
        self,
        app_id: int | str | None = None,
        token: str | None = None,
        **kwargs: Any,
    ) -> None:
        self._client = DerivClient(app_id=app_id, token=token, **kwargs)

    # ------------------------------------------------------------------
    # Async context manager — delegates to the underlying client
    # ------------------------------------------------------------------

    async def __aenter__(self) -> DerivAPI:
        await self._client.connect()
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        await self._client.disconnect()

    # ------------------------------------------------------------------
    # Connection helpers
    # ------------------------------------------------------------------

    async def connect(self) -> None:
        """Open the WebSocket connection."""
        await self._client.connect()

    async def disconnect(self) -> None:
        """Close the WebSocket connection gracefully."""
        await self._client.disconnect()

    async def authorize(self, token: str) -> dict[str, Any]:
        """
        Authorize the current session with an API token.

        Returns the raw ``authorize`` response dict which includes account
        information, scope list, and expiry details.
        """
        return await self._client.authorize(token)

    @property
    def is_connected(self) -> bool:
        return self._client.is_connected

    @property
    def is_authorized(self) -> bool:
        return self._client.is_authorized

    # ------------------------------------------------------------------
    # active_symbols
    # ------------------------------------------------------------------

    async def get_active_symbols(
        self,
        mode: str = "brief",
        contract_type: list[str] | None = None,
    ) -> list[ActiveSymbol]:
        """
        Get all currently active trading symbols.

        Parameters
        ----------
        mode:
            ``"brief"`` (default) returns a concise set of fields;
            ``"full"`` returns all available fields.
        contract_type:
            Optional list of contract types to filter by, e.g.
            ``["CALL", "PUT"]``.

        Returns
        -------
        list[ActiveSymbol]
        """
        req = ActiveSymbolsRequest(
            active_symbols=mode,
            contract_type=contract_type,
        )
        response = await self._client.send(req.to_dict())
        return [ActiveSymbol.from_dict(s) for s in response.get("active_symbols", [])]

    # ------------------------------------------------------------------
    # balance
    # ------------------------------------------------------------------

    async def get_balance(self) -> BalanceResponse:
        """
        Get the current account balance (single request, no subscription).

        Requires authorization with *trade* scope.
        """
        req = BalanceRequest(subscribe=False)
        response = await self._client.send(req.to_dict())
        return BalanceResponse.from_dict(response)

    async def stream_balance(self) -> AsyncGenerator[BalanceResponse, None]:
        """
        Subscribe to real-time balance updates.

        Yields a ``BalanceResponse`` for every change in balance.
        The first yielded item is the current balance snapshot.

        Yields
        ------
        BalanceResponse

        Example
        -------
        ::

            async for update in api.stream_balance():
                print(f"Balance: {update.balance} {update.currency}")
                if done:
                    await api.forget(update.subscription_id)
                    break
        """
        req = BalanceRequest(subscribe=True)
        async for msg in self._client.subscribe(req.to_dict()):
            yield BalanceResponse.from_dict(msg)

    # ------------------------------------------------------------------
    # buy
    # ------------------------------------------------------------------

    async def buy(
        self,
        proposal_id: str,
        price: float,
        *,
        subscribe: bool = False,
    ) -> BuyResponse:
        """
        Buy a contract using a proposal ID from a prior ``proposal`` call.

        Parameters
        ----------
        proposal_id:
            The ID obtained from a ``proposal`` response.
        price:
            Maximum price you are willing to pay.
        subscribe:
            If ``True``, the contract will stream updates after purchase.
            The subscription ID is available on ``BuyResponse.subscription_id``.

        Returns
        -------
        BuyResponse
        """
        req = BuyRequest(buy=proposal_id, price=price, subscribe=subscribe)
        response = await self._client.send(req.to_dict())
        return BuyResponse.from_dict(response)

    async def buy_with_parameters(
        self,
        parameters: BuyParameters,
        price: float,
        *,
        subscribe: bool = False,
    ) -> BuyResponse:
        """
        Buy a contract by passing parameters directly.

        In the new Deriv Options API, if direct parameter purchase is rejected,
        this automatically obtains an active price proposal and executes the buy.

        Parameters
        ----------
        parameters:
            A ``BuyParameters`` instance with ``contract_type``, ``currency``,
            ``symbol``, and any other desired fields.
        price:
            Maximum price you are willing to pay.
        subscribe:
            Stream contract updates after purchase.

        Returns
        -------
        BuyResponse
        """
        try:
            req = BuyRequest(buy="1", price=price, parameters=parameters, subscribe=subscribe)
            response = await self._client.send(req.to_dict())
            return BuyResponse.from_dict(response)
        except DerivRequestError as exc:
            if "parameters" in str(exc).lower() or "validation" in str(exc).lower():
                prop = await self.get_proposal(
                    contract_type=parameters.contract_type,
                    currency=parameters.currency,
                    underlying_symbol=parameters.symbol,
                    amount=parameters.amount or price,
                    basis=parameters.basis or "stake",
                    duration=parameters.duration,
                    duration_unit=parameters.duration_unit,
                    barrier=parameters.barrier,
                    barrier2=parameters.barrier2,
                    growth_rate=parameters.growth_rate,
                    multiplier=parameters.multiplier,
                    subscribe=True,
                )
                return await self.buy(prop.id, price=price, subscribe=subscribe)
            raise

    async def stream_buy(
        self,
        proposal_id: str,
        price: float,
    ) -> AsyncGenerator[dict[str, Any], None]:
        """
        Buy a contract and stream its open-contract updates.

        Yields raw message dicts because open-contract updates have a rich,
        variable schema.  The first yield is the buy receipt; subsequent yields
        are ``proposal_open_contract`` updates.

        Yields
        ------
        dict[str, Any]
        """
        req = BuyRequest(buy=proposal_id, price=price, subscribe=True)
        async for msg in self._client.subscribe(req.to_dict()):
            yield msg

    # ------------------------------------------------------------------
    # cancel
    # ------------------------------------------------------------------

    async def cancel(self, contract_id: int) -> CancelResponse:
        """
        Cancel a contract by its ID.

        Only certain contract types (e.g. multipliers with cancellation) support
        this operation.  Requires *trade* scope.

        Parameters
        ----------
        contract_id:
            The ``contract_id`` from your portfolio or buy receipt.
        """
        req = CancelRequest(contract_id=contract_id)
        response = await self._client.send(req.to_dict())
        return CancelResponse.from_dict(response)

    # ------------------------------------------------------------------
    # contracts_for
    # ------------------------------------------------------------------

    async def get_contracts_for(self, symbol: str) -> dict[str, Any]:
        """
        Get all available contracts and their limits for a given symbol.

        Parameters
        ----------
        symbol:
            Short symbol code, e.g. ``"R_50"`` or ``"frxEURUSD"``.

        Returns
        -------
        dict[str, Any]
            The ``contracts_for`` object as returned by the API, with an
            ``"available"`` list of contract detail dicts.
        """
        req = ContractsForRequest(symbol=symbol)
        response = await self._client.send(req.to_dict())
        return cast(dict[str, Any], response.get("contracts_for") or {})

    # ------------------------------------------------------------------
    # contract_update
    # ------------------------------------------------------------------

    async def update_contract(
        self,
        contract_id: int,
        *,
        stop_loss: float | None = None,
        take_profit: float | None = None,
    ) -> dict[str, Any]:
        """
        Update the stop-loss or take-profit on an open contract.

        Pass ``None`` to a field to cancel the existing order.
        Requires *trade* scope.

        Parameters
        ----------
        contract_id:
            Internal contract identifier.
        stop_loss:
            New stop-loss value, or ``None`` to cancel.
        take_profit:
            New take-profit value, or ``None`` to cancel.

        Returns
        -------
        dict[str, Any]
            The ``contract_update`` object from the API response.
        """
        req = ContractUpdateRequest(
            contract_id=contract_id,
            limit_order=LimitOrder(stop_loss=stop_loss, take_profit=take_profit),
        )
        response = await self._client.send(req.to_dict())
        return cast(dict[str, Any], response.get("contract_update") or {})

    # ------------------------------------------------------------------
    # contract_update_history
    # ------------------------------------------------------------------

    async def get_contract_update_history(
        self,
        contract_id: int,
        limit: int = 500,
    ) -> list[dict[str, Any]]:
        """
        Get the update history for a contract.

        Requires *trade* scope.

        Parameters
        ----------
        contract_id:
            Internal contract identifier.
        limit:
            Maximum number of history entries to return (1–999, default 500).

        Returns
        -------
        list[dict[str, Any]]
            Each item contains ``display_name``, ``order_amount``,
            ``order_date``, ``order_type``, and ``value``.
        """
        req = ContractUpdateHistoryRequest(contract_id=contract_id, limit=limit)
        response = await self._client.send(req.to_dict())
        return cast(list[dict[str, Any]], response.get("contract_update_history") or [])

    # ------------------------------------------------------------------
    # forget / forget_all
    # ------------------------------------------------------------------

    async def forget(self, stream_id: str) -> bool:
        """
        Cancel a specific real-time stream.

        Parameters
        ----------
        stream_id:
            The subscription ID from ``subscription.id`` in a stream response.

        Returns
        -------
        bool
            ``True`` if the stream existed and was cancelled, ``False`` if it
            was not found.
        """
        response = await self._client.forget_stream(stream_id)
        return bool(response.get("forget"))

    async def forget_all(self, stream_types: str | list[str]) -> list[str]:
        """
        Cancel all active streams of the given type(s).

        Parameters
        ----------
        stream_types:
            One of ``"balance"``, ``"candles"``, ``"cashier_payments"``,
            ``"proposal"``, ``"proposal_open_contract"``, ``"ticks"``,
            ``"transaction"`` — or a list of several.

        Returns
        -------
        list[str]
            IDs of the cancelled streams.

        Example
        -------
        ::

            cancelled = await api.forget_all(["ticks", "balance"])
        """
        req = ForgetAllRequest(stream_types=stream_types)
        response = await self._client.send(req.to_dict())
        return cast(list[str], response.get("forget_all") or [])

    # ------------------------------------------------------------------
    # proposal
    # ------------------------------------------------------------------

    async def get_proposal(
        self,
        contract_type: str,
        currency: str,
        underlying_symbol: str | None = None,
        *,
        symbol: str | None = None,
        amount: float | None = None,
        basis: str | None = None,
        duration: int | None = None,
        duration_unit: str | None = None,
        date_expiry: int | None = None,
        barrier: str | None = None,
        barrier2: str | None = None,
        growth_rate: float | None = None,
        multiplier: float | None = None,
        limit_order: LimitOrder | None = None,
        subscribe: bool = True,
    ) -> ProposalResponse:
        """
        Get a price proposal for a contract.

        Returns a ``ProposalResponse`` whose ``id`` can be passed directly to
        ``buy()`` to execute the trade.

        Parameters
        ----------
        contract_type:
            E.g. ``"CALL"``, ``"PUT"``, ``"ACCU"``, ``"MULTUP"``.
        currency:
            Account currency, e.g. ``"USD"``.
        underlying_symbol / symbol:
            Symbol code, e.g. ``"R_50"``.
        amount:
            Stake or payout amount (depends on ``basis``).
        basis:
            ``"stake"`` or ``"payout"``.
        duration / duration_unit:
            Contract duration, e.g. ``duration=5, duration_unit="t"`` for 5 ticks.
        date_expiry:
            Epoch expiry time (alternative to duration).
        barrier / barrier2:
            Barrier value(s) for applicable contract types.
        growth_rate:
            For Accumulator contracts.
        multiplier:
            For Multiplier contracts.
        limit_order:
            ``LimitOrder`` with ``stop_loss`` / ``take_profit`` for Multipliers.
        subscribe:
            Whether to subscribe/cache the proposal in the session (default ``True``).
            Deriv requires this to be ``True`` to buy the proposal via ``api.buy()``.
        """
        target_symbol = underlying_symbol or symbol
        if not target_symbol:
            raise ValueError("Either underlying_symbol or symbol must be provided.")

        req = ProposalRequest(
            contract_type=contract_type,
            currency=currency,
            underlying_symbol=target_symbol,
            amount=amount,
            basis=basis,
            duration=duration,
            duration_unit=duration_unit,
            date_expiry=date_expiry,
            barrier=barrier,
            barrier2=barrier2,
            growth_rate=growth_rate,
            multiplier=multiplier,
            limit_order=limit_order,
            subscribe=subscribe,
        )
        response = await self._client.send(req.to_dict())
        return ProposalResponse.from_dict(response)

    async def stream_proposal(
        self,
        contract_type: str,
        currency: str,
        underlying_symbol: str | None = None,
        *,
        symbol: str | None = None,
        **kwargs: Any,
    ) -> AsyncGenerator[ProposalResponse, None]:
        """
        Subscribe to a real-time price stream for a contract.

        Accepts the same keyword arguments as ``get_proposal()``.
        Yields ``ProposalResponse`` on every price update.

        Example
        -------
        ::

            async for price in api.stream_proposal("CALL", "USD", "R_50",
                                                    amount=10, basis="stake",
                                                    duration=5, duration_unit="t"):
                print(price.ask_price)
                break  # remember to forget the stream when done
        """
        target_symbol = underlying_symbol or symbol
        if not target_symbol:
            raise ValueError("Either underlying_symbol or symbol must be provided.")
        req = ProposalRequest(
            contract_type=contract_type,
            currency=currency,
            underlying_symbol=target_symbol,
            subscribe=True,
            **kwargs,
        )
        async for msg in self._client.subscribe(req.to_dict()):
            yield ProposalResponse.from_dict(msg)

    # ------------------------------------------------------------------
    # sell
    # ------------------------------------------------------------------

    async def sell(self, contract_id: int, price: float = 0.0) -> SellResponse:
        """
        Sell an open contract.

        Parameters
        ----------
        contract_id:
            The ``contract_id`` from your portfolio or buy receipt.
        price:
            Minimum acceptable sell price. Use ``0`` to sell at market.

        Returns
        -------
        SellResponse
        """
        req = SellRequest(contract_id=contract_id, price=price)
        response = await self._client.send(req.to_dict())
        return SellResponse.from_dict(response)

    # ------------------------------------------------------------------
    # ticks
    # ------------------------------------------------------------------

    async def stream_ticks(self, symbol: str | list[str]) -> AsyncGenerator[Tick, None]:
        """
        Subscribe to real-time tick updates for one or more symbols.

        Parameters
        ----------
        symbol:
            A single symbol string (e.g. ``"R_50"``) or a list of symbols.

        Yields
        ------
        Tick

        Example
        -------
        ::

            async for tick in api.stream_ticks("R_50"):
                print(tick.quote, tick.epoch)
        """
        req = TicksRequest(ticks=symbol, subscribe=True)
        async for msg in self._client.subscribe(req.to_dict()):
            yield Tick.from_dict(msg)

    # ------------------------------------------------------------------
    # ticks_history
    # ------------------------------------------------------------------

    async def get_ticks_history(
        self,
        symbol: str,
        *,
        end: str = "latest",
        start: int | None = None,
        count: int | None = None,
        style: str = "ticks",
        granularity: int | None = None,
        adjust_start_time: bool = False,
    ) -> dict[str, Any]:
        """
        Get historic tick data or OHLC candles for a symbol.

        Parameters
        ----------
        symbol:
            Symbol code, e.g. ``"R_50"``.
        end:
            Epoch boundary or ``"latest"``.
        start:
            Epoch start boundary (optional).
        count:
            Maximum number of ticks/candles to return.
        style:
            ``"ticks"`` (default) or ``"candles"``.
        granularity:
            Candle width in seconds (only for ``style="candles"``).
            One of: 60, 120, 180, 300, 600, 900, 1800, 3600, 7200, 14400, 28800, 86400.
        adjust_start_time:
            Adjust start time if market is closed at the boundary.

        Returns
        -------
        dict[str, Any]
            Raw response with ``history`` (for ticks) or ``candles`` key.
        """
        req = TicksHistoryRequest(
            ticks_history=symbol,
            end=end,
            start=start,
            count=count,
            style=style,
            granularity=granularity,
            adjust_start_time=adjust_start_time,
        )
        return await self._client.send(req.to_dict())

    async def stream_ticks_history(
        self,
        symbol: str,
        *,
        end: str = "latest",
        start: int | None = None,
        style: str = "ticks",
        granularity: int | None = None,
    ) -> AsyncGenerator[dict[str, Any], None]:
        """
        Subscribe to candle/tick updates after fetching history.

        Yields the initial history response, then each subsequent tick or
        OHLC update as a raw dict.
        """
        req = TicksHistoryRequest(
            ticks_history=symbol,
            end=end,
            start=start,
            style=style,
            granularity=granularity,
            subscribe=True,
        )
        async for msg in self._client.subscribe(req.to_dict()):
            yield msg

    # ------------------------------------------------------------------
    # portfolio
    # ------------------------------------------------------------------

    async def get_portfolio(self, contract_type: list[str] | None = None) -> list[dict[str, Any]]:
        """
        Get currently open contract positions.

        Requires *trade* scope.

        Parameters
        ----------
        contract_type:
            Optional list of contract types to filter by,
            e.g. ``["CALL", "PUT"]``.

        Returns
        -------
        list[dict[str, Any]]
            Each item is a contract dict from ``portfolio.contracts``.
        """
        req = PortfolioRequest(contract_type=contract_type)
        response = await self._client.send(req.to_dict())
        portfolio = response.get("portfolio") or {}
        return cast(list[dict[str, Any]], portfolio.get("contracts", []))

    # ------------------------------------------------------------------
    # profit_table
    # ------------------------------------------------------------------

    async def get_profit_table(
        self,
        *,
        limit: int = 100,
        offset: int = 0,
        date_from: int | str | None = None,
        date_to: int | str | None = None,
        description: bool = False,
        sort: str = "DESC",
    ) -> dict[str, Any]:
        """
        Get a list of sold contracts and their profit/loss.

        Requires *trade* scope.

        Returns
        -------
        dict[str, Any]
            Raw ``profit_table`` object with ``count`` and ``transactions``.
        """
        req = ProfitTableRequest(
            limit=limit,
            offset=offset,
            date_from=date_from,
            date_to=date_to,
            description=description,
            sort=sort,
        )
        response = await self._client.send(req.to_dict())
        return cast(dict[str, Any], response.get("profit_table") or {})

    # ------------------------------------------------------------------
    # statement
    # ------------------------------------------------------------------

    async def get_statement(
        self,
        *,
        limit: int = 100,
        offset: int = 0,
        date_from: int | None = None,
        date_to: int | None = None,
        action_type: str | None = None,
        description: bool = False,
    ) -> dict[str, Any]:
        """
        Get account transaction history.

        Requires *trade* scope.

        Parameters
        ----------
        action_type:
            Filter by type: ``"buy"``, ``"sell"``, ``"deposit"``, ``"withdrawal"``.

        Returns
        -------
        dict[str, Any]
            Raw ``statement`` object with ``count`` and ``transactions``.
        """
        req = StatementRequest(
            limit=limit,
            offset=offset,
            date_from=date_from,
            date_to=date_to,
            action_type=action_type,
            description=description,
        )
        response = await self._client.send(req.to_dict())
        return cast(dict[str, Any], response.get("statement") or {})

    # ------------------------------------------------------------------
    # transaction stream
    # ------------------------------------------------------------------

    async def stream_transactions(self) -> AsyncGenerator[dict[str, Any], None]:
        """
        Subscribe to real-time transaction updates.

        Requires *trade* scope. Yields raw transaction message dicts.

        Example
        -------
        ::

            async for txn in api.stream_transactions():
                print(txn.get("transaction"))
        """
        req = TransactionRequest(subscribe=True)
        async for msg in self._client.subscribe(req.to_dict()):
            yield msg

    # ------------------------------------------------------------------
    # ping / time / trading_times
    # ------------------------------------------------------------------

    async def ping(self) -> bool:
        """
        Send a ping to keep the connection alive and verify connectivity.

        Returns
        -------
        bool
            ``True`` if the server responds with ``"pong"``.
        """
        req = PingRequest()
        response = await self._client.send(req.to_dict())
        return bool(response.get("ping") == "pong")

    async def get_server_time(self) -> int:
        """
        Get the current server time as a Unix epoch integer.

        Returns
        -------
        int
            Current epoch time on the Deriv server.
        """
        req = TimeRequest()
        response = await self._client.send(req.to_dict())
        return int(response.get("time") or 0)

    async def get_trading_times(self, date: str = "today") -> dict[str, Any]:
        """
        Get market opening/closing times for a given date.

        Parameters
        ----------
        date:
            Date string in ``"yyyy-mm-dd"`` format, or ``"today"``.

        Returns
        -------
        dict[str, Any]
            Raw ``trading_times`` object with ``markets`` list.
        """
        req = TradingTimesRequest(trading_times=date)
        response = await self._client.send(req.to_dict())
        return cast(dict[str, Any], response.get("trading_times") or {})

    # ------------------------------------------------------------------
    # contracts_list
    # ------------------------------------------------------------------

    async def get_contracts_list(self) -> list[ContractCategory]:
        """
        Get all contract categories available on the platform.

        No authentication required.

        Returns
        -------
        list[ContractCategory]
            Each item has ``contract_category``, ``contract_types``, and
            ``display_name``.
        """
        req = ContractsListRequest()
        response = await self._client.send(req.to_dict())
        return [ContractCategory.from_dict(c) for c in response.get("contracts_list", [])]

    # ------------------------------------------------------------------
    # proposal_open_contract
    # ------------------------------------------------------------------

    async def get_proposal_open_contract(self, contract_id: int | None = None) -> dict[str, Any]:
        """
        Get the latest price and details for an open contract.

        Requires *trade* scope.

        Parameters
        ----------
        contract_id:
            Specific contract ID to query. If omitted, returns all open contracts.

        Returns
        -------
        dict[str, Any]
            Raw ``proposal_open_contract`` object.
        """
        req = ProposalOpenContractRequest(contract_id=contract_id, subscribe=False)
        response = await self._client.send(req.to_dict())
        return cast(dict[str, Any], response.get("proposal_open_contract") or {})

    async def stream_proposal_open_contract(
        self, contract_id: int | None = None
    ) -> AsyncGenerator[dict[str, Any], None]:
        """
        Subscribe to real-time updates for an open contract.

        Requires *trade* scope.

        Parameters
        ----------
        contract_id:
            Contract to track. If omitted, streams all open contracts.

        Yields
        ------
        dict[str, Any]
            Raw ``proposal_open_contract`` message dicts.
        """
        req = ProposalOpenContractRequest(contract_id=contract_id, subscribe=True)
        async for msg in self._client.subscribe(req.to_dict()):
            yield msg

    # ------------------------------------------------------------------
    # logout
    # ------------------------------------------------------------------

    async def logout(self) -> bool:
        """
        Log out the current session.

        Returns
        -------
        bool
            ``True`` if logout was successful.
        """
        req = LogoutRequest()
        response = await self._client.send(req.to_dict())
        return bool(response.get("logout"))

    # ------------------------------------------------------------------
    # Raw send — escape hatch for any endpoint not wrapped above
    # ------------------------------------------------------------------

    async def send(
        self, payload: dict[str, Any], *, timeout: float | None = None
    ) -> dict[str, Any]:
        """
        Send a raw request dict and return the raw response dict.

        Use this for any endpoint not yet covered by a typed method.

        Example
        -------
        ::

            resp = await api.send({"ticks": "R_50", "subscribe": 1})
        """
        return await self._client.send(payload, timeout=timeout)

    async def subscribe(
        self, payload: dict[str, Any], *, timeout: float | None = None
    ) -> AsyncGenerator[dict[str, Any], None]:
        """
        Send a subscription request and yield raw response dicts.

        Use this for any streaming endpoint not yet covered by a typed method.

        Example
        -------
        ::

            async for msg in api.subscribe({"ticks": "R_50", "subscribe": 1}):
                print(msg["tick"]["quote"])
        """
        async for msg in self._client.subscribe(payload, timeout=timeout):
            yield msg
