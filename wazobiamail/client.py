"""Compatibility import path for the WazobiaMail client.

The canonical import is ``from wazobiamail import WazobiaMail``. This module
keeps the historical ``wazobiamail.client`` path working without maintaining a
second, divergent client implementation.
"""

from __future__ import annotations

from . import Wazobia, WazobiaMail, __version__

__all__ = ["Wazobia", "WazobiaMail", "__version__"]
