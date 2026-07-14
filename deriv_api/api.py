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

    from deriv_api import DerivAPI

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
from typing import Any

from .client import DerivClient
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
    ContractUpdateHistoryRequest,
    ContractUpdateRequest,
    ContractsForRequest,
    ContractsListRequest,
    ForgetAllRequest,
    ForgetRequest,
    LimitOrder,
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

    def __init__(self, app_id: int, token: str | None = None, **kwargs: Any) -> None:
        self._client = DerivClient(app_id=app_id, token=token, **kwargs)

    # ------------------------------------------------------------------
    # Async context manager — delegates to the underlying client
    # ------------------------------------------------------------------

    async def __aenter__(self) -> "DerivAPI":
        await self._client.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
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

    async def authorize(self, token: str) -> dict:
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
        Buy a contract by passing parameters directly (no prior proposal needed).

        Parameters
        ----------
        parameters:
            A ``BuyParameters`` instance with ``contract_type``, ``currency``,
            ``underlying_symbol``, and any other desired fields.
        price:
            Maximum price you are willing to pay.
        subscribe:
            Stream contract updates after purchase.

        Returns
        -------
        BuyResponse

        Example
        -------
        ::

            params = BuyParameters(
                contract_type="CALL",
                currency="USD",
                underlying_symbol="R_50",
                amount=10.0,
                basis="stake",
                duration=5,
                duration_unit="t",
            )
            receipt = await api.buy_with_parameters(params, price=10.0)
        """
        req = BuyRequest(buy="1", price=price, parameters=parameters, subscribe=subscribe)
        response = await self._client.send(req.to_dict())
        return BuyResponse.from_dict(response)

    async def stream_buy(
        self,
        proposal_id: str,
        price: float,
    ) -> AsyncGenerator[dict, None]:
        """
        Buy a contract and stream its open-contract updates.

        Yields raw message dicts because open-contract updates have a rich,
        variable schema.  The first yield is the buy receipt; subsequent yields
        are ``proposal_open_contract`` updates.

        Yields
        ------
        dict
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

    async def get_contracts_for(self, symbol: str) -> dict:
        """
        Get all available contracts and their limits for a given symbol.

        Parameters
        ----------
        symbol:
            Short symbol code, e.g. ``"R_50"`` or ``"frxEURUSD"``.

        Returns
        -------
        dict
            The ``contracts_for`` object as returned by the API, with an
            ``"available"`` list of contract detail dicts.
        """
        req = ContractsForRequest(symbol=symbol)
        response = await self._client.send(req.to_dict())
        return response.get("contracts_for", {})

    # ------------------------------------------------------------------
    # contracts_list
    # ------------------------------------------------------------------

    async def get_contracts_list(self) -> list[ContractCategory]:
        """
        Get all contract categories available on the platform.

        Returns
        -------
        list[ContractCategory]
            Each item has ``contract_category``, ``contract_types``, and
            ``display_name``.
        """
        req = ContractsListRequest()
        response = await self._client.send(req.to_dict())
        return [
            ContractCategory.from_dict(c)
            for c in response.get("contracts_list", [])
        ]

    # ------------------------------------------------------------------
    # contract_update
    # ------------------------------------------------------------------

    async def update_contract(
        self,
        contract_id: int,
        *,
        stop_loss: float | None = None,
        take_profit: float | None = None,
    ) -> dict:
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
        dict
            The ``contract_update`` object from the API response.
        """
        req = ContractUpdateRequest(
            contract_id=contract_id,
            limit_order=LimitOrder(stop_loss=stop_loss, take_profit=take_profit),
        )
        response = await self._client.send(req.to_dict())
        return response.get("contract_update", {})

    # ------------------------------------------------------------------
    # contract_update_history
    # ------------------------------------------------------------------

    async def get_contract_update_history(
        self,
        contract_id: int,
        limit: int = 500,
    ) -> list[dict]:
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
        list[dict]
            Each item contains ``display_name``, ``order_amount``,
            ``order_date``, ``order_type``, and ``value``.
        """
        req = ContractUpdateHistoryRequest(contract_id=contract_id, limit=limit)
        response = await self._client.send(req.to_dict())
        return response.get("contract_update_history", [])

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
        return response.get("forget_all", [])

    # ------------------------------------------------------------------
    # Raw send — escape hatch for any endpoint not wrapped above
    # ------------------------------------------------------------------

    async def send(self, payload: dict[str, Any], *, timeout: float | None = None) -> dict:
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
    ) -> AsyncGenerator[dict, None]:
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
