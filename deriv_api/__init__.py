"""
deriv_api — Python client library for the Deriv API.

WebSocket API (real-time trading):

    from jav_deriv_api import DerivAPI

    async with DerivAPI(app_id=1234, token="YOUR_TOKEN") as api:
        symbols = await api.get_active_symbols()

REST API (account management):

    from jav_deriv_api import DerivRestClient

    async with DerivRestClient(app_id="1234", token="YOUR_TOKEN") as rest:
        accounts = await rest.get_accounts()

Low-level WebSocket client (escape hatch):

    from jav_deriv_api import DerivClient

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

# Resolve candidate .env paths:
# 1. Current working directory (application's .env)
# 2. Project root
# 3. Package directory (library defaults such as DERIV_APP_ID)
_pkg_dir = Path(__file__).parent
_candidates = [
    Path.cwd() / ".env",
    _pkg_dir.parent / ".env",
    _pkg_dir / ".env",
]
for _env_path in _candidates:
    if _env_path.exists():
        _load_dotenv(_env_path, override=False)  # override=False: app settings take priority

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
    ContractCategory,
    ContractsForRequest,
    ContractsListRequest,
    ContractUpdateHistoryRequest,
    ContractUpdateRequest,
    CreateAccountRequest,
    ForgetAllRequest,
    ForgetRequest,
    LegacyAccount,
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
    "ContractsListRequest",
    "ContractUpdateRequest",
    "ContractUpdateHistoryRequest",
    "CreateAccountRequest",
    "ForgetRequest",
    "ForgetAllRequest",
    "LimitOrder",
    "LogoutRequest",
    "PingRequest",
    "PortfolioRequest",
    "ProfitTableRequest",
    "ProposalOpenContractRequest",
    "ProposalRequest",
    "SellRequest",
    "StatementRequest",
    "TicksRequest",
    "TicksHistoryRequest",
    "TimeRequest",
    "TradingTimesRequest",
    "TransactionRequest",
    # Models — responses / data
    "ActiveSymbol",
    "AccountInfo",
    "BalanceResponse",
    "BuyResponse",
    "CancelResponse",
    "ContractCategory",
    "LegacyAccount",
    "ProposalResponse",
    "SellResponse",
    "Tick",
]

__version__ = "0.2.1"
