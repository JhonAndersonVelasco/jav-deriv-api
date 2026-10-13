"""Compatibility module: aliases 'deriv_api' as 'jav_deriv_api'."""

import sys

import deriv_api
from deriv_api import *  # noqa: F403

sys.modules["jav_deriv_api"] = deriv_api
