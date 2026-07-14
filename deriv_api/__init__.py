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
"""

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
    ContractUpdateHistoryRequest,
    ContractUpdateRequest,
    ContractsForRequest,
    ContractsListRequest,
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
    "ContractsListRequest",
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
    "ContractCategory",
    "LegacyAccount",
]

__version__ = "0.1.0"
