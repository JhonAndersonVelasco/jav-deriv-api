"""
Core WebSocket client for the Deriv API.

Handles connection lifecycle, request/response correlation, subscriptions,
automatic reconnection, and ping/keepalive.

Usage (async context manager — recommended):

    async with DerivClient(app_id=1234) as client:
        await client.authorize("YOUR_TOKEN")
        response = await client.send({"active_symbols": "brief"})

Or manually:

    client = DerivClient(app_id=1234)
    await client.connect()
    ...
    await client.disconnect()
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
from collections.abc import AsyncGenerator, Callable
from types import TracebackType
from typing import Any, cast

import websockets
import websockets.connection
from websockets.exceptions import ConnectionClosed

from .exceptions import (
    DerivConnectionError,
    DerivRequestError,
    DerivTimeoutError,
)

logger = logging.getLogger(__name__)

# Default Deriv WebSocket endpoint
_DEFAULT_WS_URL = os.environ.get("DERIV_ENDPOINT", "wss://red.derivws.com/websockets/v3")
_DEFAULT_APP_ID = "34FoD4WDTegRoduFd3jkt"

# Sentinel used to close subscription async-generators cleanly
_STREAM_CLOSE = object()


class DerivClient:
    """
    Async WebSocket client for the Deriv API.

    Parameters
    ----------
    app_id:
        Your Deriv application ID. If not provided, defaults to ``DERIV_APP_ID``,
        or ``1089``.
    token:
        Optional API token. If not provided, defaults to ``DERIV_TOKEN``.
        If a Personal Access Token (PAT, starting with ``pat_``) is used,
        the client automatically resolves the WebSocket URL via OTP.
    endpoint:
        WebSocket URL. Defaults to the production Deriv endpoint.
    account_id:
        Optional account ID to trade on (e.g. ``"DOT93852030"``) when using OTP.
    request_timeout:
        Seconds to wait for a response before raising ``DerivTimeoutError``.
    ping_interval:
        Seconds between keepalive pings sent to the server.
    reconnect:
        Whether to attempt automatic reconnection on unexpected disconnections.
    reconnect_attempts:
        Maximum number of consecutive reconnection attempts (0 = unlimited).
    reconnect_delay:
        Base delay (seconds) between reconnection attempts; grows with backoff.
    """

    def __init__(
        self,
        app_id: int | str | None = None,
        token: str | None = None,
        endpoint: str | None = None,
        account_id: str | None = None,
        request_timeout: float = 30.0,
        ping_interval: float = 30.0,
        reconnect: bool = True,
        reconnect_attempts: int = 5,
        reconnect_delay: float = 2.0,
    ) -> None:
        if app_id is None:
            env_app_id = os.environ.get("DERIV_APP_ID")
            app_id = env_app_id if env_app_id is not None else _DEFAULT_APP_ID
        self.app_id = app_id
        if token is None:
            token = os.environ.get("DERIV_TOKEN")
        self.token = token
        if endpoint is None:
            endpoint = os.environ.get("DERIV_ENDPOINT", _DEFAULT_WS_URL)
        self.endpoint = endpoint
        self.account_id = account_id
        self.request_timeout = request_timeout
        self.ping_interval = ping_interval
        self.reconnect = reconnect
        self.reconnect_attempts = reconnect_attempts
        self.reconnect_delay = reconnect_delay

        self._ws: websockets.ClientConnection | None = None
        self._req_id: int = 0
        self._pending: dict[int, asyncio.Future[dict[str, Any]]] = {}
        # subscription_id -> asyncio.Queue
        self._subscriptions: dict[str, asyncio.Queue[Any]] = {}
        # msg_type -> list of callback(dict)
        self._stream_callbacks: dict[str, list[Callable[[dict[str, Any]], Any]]] = {}

        self._recv_task: asyncio.Task[None] | None = None
        self._ping_task: asyncio.Task[None] | None = None
        self._lock = asyncio.Lock()
        self._connected = asyncio.Event()
        self._closing = False
        self._authorized = False

    # ------------------------------------------------------------------
    # Connection management
    # ------------------------------------------------------------------

    def _build_url(self) -> str:
        if "otp=" in self.endpoint:
            return self.endpoint
        separator = "&" if "?" in self.endpoint else "?"
        # Legacy websockets/v3 expects a numeric app_id; if using OAuth string, default to 1089
        app_id_val = self.app_id
        if isinstance(app_id_val, str) and not app_id_val.isdigit():
            app_id_val = 1089
        return f"{self.endpoint}{separator}app_id={app_id_val}"

    def _is_ws_open(self) -> bool:
        """Return True if the WebSocket connection is currently open."""
        if self._ws is None:
            return False
        # websockets >= 14 uses a State enum; older versions had a .closed bool.
        state = getattr(self._ws, "state", None)
        if state is not None:
            return bool(state is websockets.connection.State.OPEN)
        # Fallback for any older installation that still has .closed
        return not getattr(self._ws, "closed", True)

    async def connect(self) -> None:
        """Open the WebSocket connection and start background tasks."""
        if self._ws is not None and self._is_ws_open():
            return
        self._closing = False

        # If using a Personal Access Token (PAT) and not already on an OTP URL,
        # resolve the pre-authenticated WebSocket URL via DerivRestClient
        needs_otp = self.token and (self.token.startswith("pat_") or self.account_id)
        if needs_otp and "otp=" not in self.endpoint:
            from .rest_client import DerivRestClient

            async with DerivRestClient(app_id=self.app_id, token=self.token) as rest:
                target_account_id = self.account_id
                if not target_account_id:
                    accounts = await rest.get_accounts()
                    demo_accs = [
                        a
                        for a in accounts
                        if a.account_type == "demo" or a.account_id.startswith("D")
                    ]
                    target = demo_accs[0] if demo_accs else (accounts[0] if accounts else None)
                    if target:
                        target_account_id = target.account_id
                if target_account_id:
                    self.endpoint = await rest.get_otp_url(target_account_id)

        await self._do_connect()

    async def _do_connect(self) -> None:
        url = self._build_url()
        logger.debug("Connecting to %s", url)
        try:
            self._ws = await websockets.connect(
                url,
                ping_interval=None,  # we manage our own keepalive
                close_timeout=5,
            )
        except Exception as exc:
            # Fallback if ws.derivws.com fails
            if "ws.derivws.com" in url and "otp=" not in url:
                fallback_url = url.replace("ws.derivws.com", "red.derivws.com")
                logger.warning(
                    "Connection to %s failed (%s). Retrying fallback %s...",
                    url,
                    exc,
                    fallback_url,
                )
                try:
                    self._ws = await websockets.connect(
                        fallback_url,
                        ping_interval=None,
                        close_timeout=5,
                    )
                    url = fallback_url
                    self.endpoint = self.endpoint.replace("ws.derivws.com", "red.derivws.com")
                except Exception as fb_exc:
                    err_msg = f"Failed to connect to {url}: {exc}; fallback failed: {fb_exc}"
                    raise DerivConnectionError(err_msg) from fb_exc
            else:
                raise DerivConnectionError(f"Failed to connect to {url}: {exc}") from exc

        self._connected.set()
        # If connecting via an OTP URL, session is pre-authorized by Deriv
        self._authorized = "otp=" in url
        logger.info("Connected to Deriv API (%s)", url)

        # Start background receiver and pinger
        self._recv_task = asyncio.create_task(self._recv_loop(), name="deriv_recv")
        self._ping_task = asyncio.create_task(self._ping_loop(), name="deriv_ping")

        # Auto-authorize if a token was provided and not using OTP
        if self.token and not self._authorized:
            await self.authorize(self.token)

    async def disconnect(self) -> None:
        """Close the WebSocket connection gracefully."""
        self._closing = True
        self._connected.clear()

        for task in (self._ping_task, self._recv_task):
            if task and not task.done():
                try:
                    task.cancel()
                except Exception:
                    pass
                try:
                    await task
                except (asyncio.CancelledError, Exception):
                    pass

        if self._ws and self._is_ws_open():
            try:
                await self._ws.close()
            except Exception:
                pass
        self._ws = None
        self._authorized = False

        # Drain all pending futures with a connection error
        err = DerivConnectionError("Connection closed.")
        for fut in self._pending.values():
            if not fut.done():
                try:
                    fut.set_exception(err)
                except Exception:
                    pass
        self._pending.clear()

        # Signal all subscription queues to close
        for queue in self._subscriptions.values():
            try:
                await queue.put(_STREAM_CLOSE)
            except Exception:
                pass
        self._subscriptions.clear()

        logger.info("Disconnected from Deriv API.")

    async def close(self) -> None:
        """Close the WebSocket connection gracefully (alias for disconnect)."""
        await self.disconnect()

    async def _reconnect_loop(self) -> None:
        """Attempt to reconnect with exponential backoff."""
        attempts = 0
        delay = self.reconnect_delay
        while not self._closing:
            attempts += 1
            if self.reconnect_attempts and attempts > self.reconnect_attempts:
                logger.error("Max reconnection attempts (%d) reached.", self.reconnect_attempts)
                return
            logger.warning("Reconnecting (attempt %d) in %.1fs …", attempts, delay)
            await asyncio.sleep(delay)
            delay = min(delay * 2, 60.0)  # cap at 60 s
            try:
                await self._do_connect()
                logger.info("Reconnected successfully.")
                return
            except DerivConnectionError as exc:
                logger.warning("Reconnect failed: %s", exc)

    # ------------------------------------------------------------------
    # Background loops
    # ------------------------------------------------------------------

    async def _recv_loop(self) -> None:
        """Continuously read messages from the WebSocket and dispatch them."""
        while True:
            if self._ws is None:
                break
            try:
                raw = await self._ws.recv()
            except ConnectionClosed:
                logger.warning("WebSocket connection closed unexpectedly.")
                self._connected.clear()
                if not self._closing and self.reconnect:
                    asyncio.create_task(self._reconnect_loop())
                return
            except asyncio.CancelledError:
                return

            try:
                message: dict[str, Any] = json.loads(raw)
            except json.JSONDecodeError:
                logger.warning("Received non-JSON message: %s", raw[:200])
                continue

            await self._dispatch(message)

    async def _ping_loop(self) -> None:
        """Send periodic pings to keep the connection alive."""
        while True:
            try:
                await asyncio.sleep(self.ping_interval)
                if self._ws and self._is_ws_open():
                    await self._ws.ping()
            except (ConnectionClosed, asyncio.CancelledError):
                return

    # ------------------------------------------------------------------
    # Message dispatch
    # ------------------------------------------------------------------

    async def _dispatch(self, message: dict[str, Any]) -> None:
        """Route an incoming message to its pending future or subscription queue."""
        if "error" in message:
            req_id = message.get("req_id")
            if req_id and req_id in self._pending:
                self._pending.pop(req_id).set_exception(DerivRequestError.from_response(message))
            else:
                logger.error("API error (unsolicited): %s", message["error"])
            return

        req_id = message.get("req_id")
        msg_type = message.get("msg_type", "")
        sub_info = message.get("subscription", {})
        sub_id = sub_info.get("id") if sub_info else None

        # --- Deliver to one-shot pending future (if this is a direct response)
        if req_id and req_id in self._pending:
            fut = self._pending[req_id]
            # For subscription responses the first message resolves the future;
            # subsequent stream messages go to the queue.
            if not fut.done():
                fut.set_result(message)
                # If there's a subscription queue registered, don't pop the future yet —
                # it was already resolved; subsequent messages will hit the sub_id branch.
                if sub_id is None:
                    self._pending.pop(req_id, None)
                else:
                    self._pending.pop(req_id, None)
                    # The queue is registered by send_and_subscribe; put the first
                    # message into it too so the caller gets it in the stream.
                    if sub_id in self._subscriptions:
                        await self._subscriptions[sub_id].put(message)
            return

        # --- Stream (subscription) message
        if sub_id and sub_id in self._subscriptions:
            await self._subscriptions[sub_id].put(message)
            return

        # --- Named callbacks
        if msg_type in self._stream_callbacks:
            for cb in self._stream_callbacks[msg_type]:
                try:
                    if asyncio.iscoroutinefunction(cb):
                        await cb(message)
                    else:
                        cb(message)
                except Exception:
                    logger.exception("Error in stream callback for %s", msg_type)
            return

        logger.debug("Unhandled message (msg_type=%s, req_id=%s)", msg_type, req_id)

    # ------------------------------------------------------------------
    # Public send interface
    # ------------------------------------------------------------------

    def _next_req_id(self) -> int:
        self._req_id += 1
        return self._req_id

    async def send(
        self,
        payload: dict[str, Any],
        *,
        timeout: float | None = None,
    ) -> dict[str, Any]:
        """
        Send a request and wait for the corresponding response.

        Parameters
        ----------
        payload:
            Raw API request dict (without ``req_id``; one is added automatically).
        timeout:
            Override the client-level ``request_timeout`` for this call.

        Returns
        -------
        dict[str, Any]
            The raw API response dict (with ``echo_req``, ``msg_type``, etc.).

        Raises
        ------
        DerivConnectionError
            If the client is not connected.
        DerivRequestError
            If the API returns an error.
        DerivTimeoutError
            If no response arrives within the timeout.
        """
        if self._ws is None or not self._is_ws_open():
            raise DerivConnectionError("Not connected. Call connect() first.")

        req_id = self._next_req_id()
        payload = {**payload, "req_id": req_id}

        loop = asyncio.get_running_loop()
        fut: asyncio.Future[dict[str, Any]] = loop.create_future()
        self._pending[req_id] = fut

        await self._ws.send(json.dumps(payload))
        logger.debug("→ %s (req_id=%d)", payload.get("msg_type") or list(payload.keys())[0], req_id)

        wait = timeout if timeout is not None else self.request_timeout
        try:
            result = await asyncio.wait_for(asyncio.shield(fut), timeout=wait)
        except asyncio.TimeoutError:
            self._pending.pop(req_id, None)
            raise DerivTimeoutError(f"Request timed out after {wait}s (req_id={req_id})")

        logger.debug("← %s (req_id=%d)", result.get("msg_type"), req_id)
        return result

    async def subscribe(
        self,
        payload: dict[str, Any],
        *,
        timeout: float | None = None,
    ) -> AsyncGenerator[dict[str, Any], None]:
        """
        Send a subscription request and yield incoming stream messages.

        The first yielded message is the initial response; subsequent messages
        are real-time updates.

        Parameters
        ----------
        payload:
            API request dict. Should include ``"subscribe": 1`` if required.
        timeout:
            Timeout for receiving the initial response.

        Yields
        ------
        dict[str, Any]
            Raw API message dicts from the stream.

        Example
        -------
        ::

            async for msg in client.subscribe({"balance": 1, "subscribe": 1}):
                print(msg["balance"]["balance"])
        """
        if self._ws is None or not self._is_ws_open():
            raise DerivConnectionError("Not connected. Call connect() first.")

        req_id = self._next_req_id()
        payload = {**payload, "req_id": req_id}

        queue: asyncio.Queue[Any] = asyncio.Queue()
        loop = asyncio.get_running_loop()
        fut: asyncio.Future[dict[str, Any]] = loop.create_future()
        self._pending[req_id] = fut

        await self._ws.send(json.dumps(payload))
        logger.debug("→ subscribe %s (req_id=%d)", list(payload.keys())[0], req_id)

        wait = timeout if timeout is not None else self.request_timeout
        try:
            first = await asyncio.wait_for(asyncio.shield(fut), timeout=wait)
        except asyncio.TimeoutError:
            self._pending.pop(req_id, None)
            raise DerivTimeoutError(f"Subscription timed out after {wait}s (req_id={req_id})")

        sub_info = first.get("subscription", {})
        sub_id = sub_info.get("id") if sub_info else None

        if sub_id:
            # Register queue so future stream messages land here
            self._subscriptions[sub_id] = queue

        yield first

        if not sub_id:
            # Not a streaming response — nothing more to yield
            return

        try:
            while True:
                try:
                    item = await asyncio.wait_for(queue.get(), timeout=60.0)
                except asyncio.TimeoutError:
                    # Just keep waiting — no message is fine for slow streams
                    continue

                if item is _STREAM_CLOSE:
                    break
                yield cast(dict[str, Any], item)
        finally:
            self._subscriptions.pop(sub_id, None)

    async def forget_stream(self, stream_id: str) -> dict[str, Any]:
        """
        Unsubscribe from a specific stream.

        Parameters
        ----------
        stream_id:
            The subscription ID returned in the ``subscription.id`` field.
        """
        result = await self.send({"forget": stream_id})
        # Clean up the local queue if still registered
        if stream_id in self._subscriptions:
            await self._subscriptions[stream_id].put(_STREAM_CLOSE)
            self._subscriptions.pop(stream_id, None)
        return result

    async def forget_all_streams(self, stream_types: str | list[str]) -> dict[str, Any]:
        """Unsubscribe from all streams of the given type(s)."""
        return await self.send({"forget_all": stream_types})

    # ------------------------------------------------------------------
    # Authorization
    # ------------------------------------------------------------------

    async def authorize(self, token: str) -> dict[str, Any]:
        """
        Authorize the session with an API token.

        Parameters
        ----------
        token:
            The Deriv API token for the account.

        Returns
        -------
        dict[str, Any]
            Raw ``authorize`` response.
        """
        response = await self.send({"authorize": token})
        self._authorized = True
        self.token = token
        logger.info("Authorized as %s", response.get("authorize", {}).get("loginid"))
        return response

    @property
    def is_connected(self) -> bool:
        """True if the WebSocket is currently open."""
        return self._is_ws_open()

    @property
    def is_authorized(self) -> bool:
        """True if the session has been successfully authorized."""
        return self._authorized

    # ------------------------------------------------------------------
    # Async context manager
    # ------------------------------------------------------------------

    async def __aenter__(self) -> DerivClient:
        await self.connect()
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        await self.disconnect()
