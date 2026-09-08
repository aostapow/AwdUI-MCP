"""Core contract for AwdUI MCP addins."""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Optional


@dataclass
class AddinManifest:
    id: str
    name: str
    version: str
    entry_module: str
    enabled_by_default: bool = False
    match: dict[str, Any] = field(default_factory=dict)
    skills: list[str] = field(default_factory=list)
    tool_namespace: str = ""


@dataclass
class AddinContext:
    """Services exposed to addins — no direct server internals."""

    data_dir: Path
    addin_root: Path
    manifest: AddinManifest
    log: Callable[[str], None]
    get_target_window: Callable[[], Optional[str]]


class AwduiAddin(ABC):
    manifest: AddinManifest

    def on_load(self, ctx: AddinContext) -> None:
        """Optional: validate deps, warm caches."""

    @abstractmethod
    def register_tools(self, mcp: Any, ctx: AddinContext) -> int:
        """Register MCP tools; return count."""

    def match_app(self, identity: dict, ctx: AddinContext) -> float:
        """Return 0.0–1.0 confidence this addin applies to the current window."""
        return 0.0

    def enrich_control_interaction(
        self,
        element: dict,
        base: dict,
        ctx: AddinContext,
    ) -> dict:
        return base

    def on_shutdown(self, ctx: AddinContext) -> None:
        pass
