"""Shared upstream HTTP and authentication clients."""

from .authentication import AuthenticationProvider
from .http import NeteaseHttpClient

__all__ = ["AuthenticationProvider", "NeteaseHttpClient"]
