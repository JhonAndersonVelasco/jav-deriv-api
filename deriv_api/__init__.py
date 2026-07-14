"""
deriv_api — Python client library for the Deriv API.

WebSocket API (real-time trading):

    from deriv_api import DerivAPI

    async with DerivAPI(app_id=1234, token="YOUR_TOKEN") as api:
        symbols = await api.get_active_symbols()

REST API (account management):

    from deriv_api import DerivRestClient

    async with DerivRestClient(app_id="1234", token="YOUR_TOKEN") as rest:
        accounts = await rest.get_accounts()

Low-level WebSocket client (escape hatch):

    from deriv_api import DerivClient

    async with DerivClient(app_id=1234) as client:
        await client.authorize("YOUR_TOKEN")
        response = await client.send({"active_symbols": "brief"})

Environment variables are loaded automatically from a .env file located in:
  1. The project root (two levels up from this package, where pyproject.toml lives)
  2. The package directory (deriv_api/.env) — fallback

Run ``deriv-setup`` after installation to create the .env interactively.
"""

from pathlib import Path

from dotenv import load_dotenv as _load_dotenv

# Resolve candidate .env paths: project root first, then package dir as fallback.
_pkg_dir = Path(__file__).parent
_candidates = [
    _pkg_dir.parent / ".env",  # project root
    _pkg_dir / ".env",         # deriv_api/.env
]
for _env_path in _candidates:
    if _env_path.exists():
        _load_dotenv(_env_path, override=False)  # override=False: env vars already set take priority
        break

from .api import DerivAPI
from .client import DerivClient
from .exceptions import (
    DerivAPIError,
    DerivAuthError,
    DerivConnectionError,
    DerivRequestError,
    DerivStreamError,
    DerivTimeoutError,
    DerivValidationError,
)
from .models import (
    AccountInfo,
    ActiveSymbol,
    ActiveSymbolsRequest,
    BalanceRequest,
    BalanceResponse,
    BuyParameters,
    BuyRequest,
    BuyResponse,
    CancelRequest,
    CancelResponse,
    ContractUpdateHistoryRequest,
    ContractUpdateRequest,
    ContractsForRequest,
    CreateAccountRequest,
    ForgetAllRequest,
    ForgetRequest,
    LegacyAccount,
    LimitOrder,
)
from .rest_client import DerivRestClient

__all__ = [
    # High-level clients
    "DerivAPI",
    "DerivRestClient",
    # Low-level client
    "DerivClient",
    # Exceptions
    "DerivAPIError",
    "DerivAuthError",
    "DerivConnectionError",
    "DerivRequestError",
    "DerivStreamError",
    "DerivTimeoutError",
    "DerivValidationError",
    # Models — requests
    "ActiveSymbolsRequest",
    "BalanceRequest",
    "BuyParameters",
    "BuyRequest",
    "CancelRequest",
    "ContractsForRequest",
    "ContractUpdateRequest",
    "ContractUpdateHistoryRequest",
    "CreateAccountRequest",
    "ForgetRequest",
    "ForgetAllRequest",
    "LimitOrder",
    # Models — responses / data
    "ActiveSymbol",
    "AccountInfo",
    "BalanceResponse",
    "BuyResponse",
    "CancelResponse",
    "LegacyAccount",
]

__version__ = "0.1.0"
