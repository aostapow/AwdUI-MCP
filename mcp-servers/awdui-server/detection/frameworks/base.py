"""Framework-specific detection/act policies (agnostic of product apps)."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional, Sequence


@dataclass(frozen=True)
class FrameworkProfile:
    """Policies for one UI framework family — keep product-specific rules out of MCP core."""

    key: str
    aliases: tuple[str, ...] = ()
    auto_list_depth: int = 20
    backend_order: tuple[str, ...] = ("uia", "flaui", "msaa", "win32", "jab")
    prefers_spy_invoke: bool = False
    prefers_spy_expand_collapse: bool = False
    expander_dims_via_spy: bool = False
    quick_resolve_spy_before_find: bool = False

    def normalized_key(self, framework: str) -> bool:
        fw = (framework or "").strip().lower()
        if fw == self.key:
            return True
        return fw in self.aliases

    def weak_backend_result(self, backend_name: str, elements: Sequence[Any]) -> bool:
        """True when backend tree is low-value for this framework (orchestrator skip)."""
        from detection.frameworks.policies import weak_backend_result

        return weak_backend_result(self.key, backend_name, elements)
