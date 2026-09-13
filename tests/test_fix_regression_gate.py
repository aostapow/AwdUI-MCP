"""Regression matrix gate for generic fixes on shared detection core."""
from __future__ import annotations

from fix_in_cycle_gate import audit_fix_regression_scope


def test_generic_shared_core_requires_regression_frameworks():
    state = {
        "active_lab": "Escritorio",
        "last_cycle": {
            "flow_id": "F-1",
            "fix_gate": {
                "abstraction": "generic",
                "framework": "win32",
                "files_touched": [
                    "mcp-servers/awdui-server/detection/backends/uia_backend.py",
                ],
                "regression_frameworks": ["win32"],
            },
        },
    }
    result = audit_fix_regression_scope(state)
    assert result.blocked is True
    assert result.reason == "generic_fix_without_regression_matrix"


def test_framework_abstraction_skips_regression_gate():
    state = {
        "active_lab": "Calc",
        "last_cycle": {
            "fix_gate": {
                "abstraction": "framework",
                "files_touched": ["mcp-servers/awdui-server/detection/backends/uia_backend.py"],
            },
        },
    }
    assert audit_fix_regression_scope(state).blocked is False
