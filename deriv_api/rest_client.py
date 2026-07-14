"""
REST HTTP client for Deriv API endpoints that use HTTP rather than WebSocket.

Covers:
  - GET  /v1/health
  - GET  /trading/v1/options/accounts
  - POST /trading/v1/options/accounts
  - GET  /trading/v1/options/legacy/accounts
  - GET  /trading/v1/options/legacy/migration-status

All methods are async and use ``aiohttp`` under the hood.  The client can be
used as an async context manager or managed manually.

Base URL: https://api.derivws.com

Usage
-----
::

    from jav_deriv_api import DerivRestClient

    async with DerivRestClient(app_id="1234", token="Bearer YOUR_TOKEN") as rest:
        ok = await rest.health()
        accounts = await rest.get_accounts()
        for acc in accounts:
            print(acc.account_id, acc.balance, acc.currency)
"""

from __future__ import annotations

import logging
from typing import Any

import aiohttp

from .exceptions import DerivAPIError, DerivAuthError, DerivConnectionError, DerivRequestError
from .models import AccountInfo, CreateAccountRequest, LegacyAccount

logger = logging.getLogger(__name__)

_DEFAULT_BASE_URL = "https://api.derivws.com"
_DEFAULT_TRADING_URL = "https://api.derivws.com"


class DerivRestClient:
    """
    Async REST client for Deriv HTTP API endpoints.

    Parameters
    ----------
    app_id:
        Your Deriv application ID (sent as the ``Deriv-App-ID`` header).
    token:
        Bearer token for authenticated endpoints.  Pass the full string
        including ``"Bearer "`` prefix, or just the raw token — the client
        normalises it.
    base_url:
        Root URL for all API calls. Defaults to ``https://api.derivws.com``.
    timeout:
        Total request timeout in seconds.
    """

    def __init__(
        self,
        app_id: str | int,
        token: str | None = None,
        base_url: str = _DEFAULT_BASE_URL,
        timeout: float = 30.0,
    ) -> None:
        self.app_id = str(app_id)
        self.token = self._normalise_token(token) if token else None
        self.base_url = base_url.rstrip("/")
        self._timeout = aiohttp.ClientTimeout(total=timeout)
        self._session: aiohttp.ClientSession | None = None

    # ------------------------------------------------------------------
    # Token helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _normalise_token(token: str) -> str:
        """Ensure the token string starts with 'Bearer '."""
        token = token.strip()
        if not token.lower().startswith("bearer "):
            return f"Bearer {token}"
        return token

    # ------------------------------------------------------------------
    # Session management
    # ------------------------------------------------------------------

    async def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(timeout=self._timeout)
        return self._session

    async def close(self) -> None:
        """Close the underlying aiohttp session."""
        if self._session and not self._session.closed:
            await self._session.close()
        self._session = None

    async def __aenter__(self) -> "DerivRestClient":
        await self._get_session()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        await self.close()

    # ------------------------------------------------------------------
    # Internal request helper
    # ------------------------------------------------------------------

    def _build_headers(self, *, auth: bool = False) -> dict[str, str]:
        headers: dict[str, str] = {"Deriv-App-ID": self.app_id}
        if auth:
            if not self.token:
                raise DerivAuthError(
                    "This endpoint requires authentication. "
                    "Provide a token when constructing DerivRestClient."
                )
            headers["Authorization"] = self.token
        return headers

    async def _request(
        self,
        method: str,
        url: str,
        *,
        auth: bool = False,
        json_body: dict | None = None,
        params: dict | None = None,
    ) -> Any:
        session = await self._get_session()
        headers = self._build_headers(auth=auth)
        if json_body is not None:
            headers["Content-Type"] = "application/json"

        logger.debug("%s %s", method.upper(), url)

        try:
            async with session.request(
                method,
                url,
                headers=headers,
                json=json_body,
                params=params,
            ) as resp:
                # Handle plain-text responses (e.g. health check)
                content_type = resp.content_type or ""
                if "json" in content_type:
                    body = await resp.json()
                else:
                    body = await resp.text()

                if resp.status >= 400:
                    # Try to extract a meaningful error message
                    if isinstance(body, dict):
                        msg = body.get("message") or body.get("error") or str(body)
                        code = body.get("code") or str(resp.status)
                    else:
                        msg = str(body)
                        code = str(resp.status)

                    if resp.status in (401, 403):
                        raise DerivAuthError(msg, code=code)
                    raise DerivRequestError(msg, code=code, details=body if isinstance(body, dict) else {})

                return body

        except aiohttp.ClientConnectionError as exc:
            raise DerivConnectionError(f"Connection error: {exc}") from exc
        except aiohttp.ClientResponseError as exc:
            raise DerivRequestError(str(exc), code=str(exc.status)) from exc

    # ------------------------------------------------------------------
    # Health
    # ------------------------------------------------------------------

    async def health(self) -> bool:
        """
        Check whether the Deriv Options API is healthy.

        Returns
        -------
        bool
            ``True`` if the service responds with ``"OK"``.
        """
        url = f"{self.base_url}/v1/health"
        result = await self._request("GET", url)
        return str(result).strip().upper() == "OK"

    # ------------------------------------------------------------------
    # Accounts
    # ------------------------------------------------------------------

    async def get_accounts(self) -> list[AccountInfo]:
        """
        Retrieve all Options trading accounts for the authenticated user.

        Requires a valid token.

        Returns
        -------
        list[AccountInfo]
        """
        url = f"{self.base_url}/trading/v1/options/accounts"
        body = await self._request("GET", url, auth=True)
        items = body.get("data", []) if isinstance(body, dict) else body
        return [AccountInfo.from_dict(a) for a in items]

    async def create_account(
        self,
        account_type: str = "demo",
        currency: str = "USD",
        group: str = "row",
    ) -> list[AccountInfo] | AccountInfo:
        """
        Create a new Options trading account.

        Returns ``AccountInfo`` if the account already existed (HTTP 200), or a
        ``list[AccountInfo]`` for a newly created account (HTTP 201).

        Parameters
        ----------
        account_type:
            ``"demo"`` or ``"real"``.
        currency:
            Account currency (currently only ``"USD"`` is supported).
        group:
            Account group (currently only ``"row"`` is supported).

        Returns
        -------
        AccountInfo | list[AccountInfo]
        """
        url = f"{self.base_url}/trading/v1/options/accounts"
        req = CreateAccountRequest(
            account_type=account_type,
            currency=currency,
            group=group,
        )
        body = await self._request("POST", url, auth=True, json_body=req.to_dict())
        data = body.get("data", body) if isinstance(body, dict) else body
        if isinstance(data, list):
            return [AccountInfo.from_dict(a) for a in data]
        return AccountInfo.from_dict(data)

    # ------------------------------------------------------------------
    # Legacy accounts
    # ------------------------------------------------------------------

    async def get_legacy_accounts(self) -> dict[str, list[LegacyAccount]]:
        """
        Get the authenticated user's legacy accounts grouped by login ID.

        Returns
        -------
        dict[str, list[LegacyAccount]]
            Keys are login IDs (e.g. ``"CR0001"``); values are lists of
            ``LegacyAccount`` objects with ``account_id`` and ``currency``.
        """
        url = f"{self.base_url}/trading/v1/options/legacy/accounts"
        body = await self._request("GET", url, auth=True)
        loginids: dict = body.get("loginids", {}) if isinstance(body, dict) else {}
        return {
            loginid: [LegacyAccount.from_dict(a) for a in accounts]
            for loginid, accounts in loginids.items()
        }

    # ------------------------------------------------------------------
    # Legacy migration status
    # ------------------------------------------------------------------

    async def get_legacy_migration_status(self) -> str:
        """
        Get the current state of the user's platform upgrade.

        Returns
        -------
        str
            One of ``"complete"``, ``"pending"``, ``"failed"``,
            ``"not_applicable"``.
        """
        url = f"{self.base_url}/trading/v1/options/legacy/migration-status"
        body = await self._request("GET", url, auth=True)
        return body.get("status", "") if isinstance(body, dict) else str(body)
