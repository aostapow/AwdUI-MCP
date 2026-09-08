"""Addin SDK — contract between AwdUI MCP core and detachable product plugins."""
from __future__ import annotations

from addin_sdk.contract import AddinContext, AddinManifest, AwduiAddin
from addin_sdk.registry import AddinRegistry, bootstrap_addins, get_registry, shutdown_addins

__all__ = [
    "AddinContext",
    "AddinManifest",
    "AwduiAddin",
    "AddinRegistry",
    "bootstrap_addins",
    "get_registry",
    "shutdown_addins",
]
