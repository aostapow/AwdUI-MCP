"""Tests for framework catalog API payload."""
from __future__ import annotations


def test_build_framework_catalog_has_frameworks_and_controls():
    from detection.framework_catalog import build_framework_catalog

    cat = build_framework_catalog(include_stored=False)
    assert cat["schema_version"] == 1
    assert any(f["id"] == "winforms" for f in cat["frameworks"])
    assert any(f["id"] == "uwp" for f in cat["frameworks"])
    roles = {c["role"] for c in cat["uia_controls"]}
    assert "Button" in roles
    assert "ComboBox" in roles
    swf = {c["swf_class"] for c in cat["swf_classes"]}
    assert "SwfButton" in swf
    btn = next(c for c in cat["swf_classes"] if c["swf_class"] == "SwfButton")
    method_names = {m["name"] for m in btn["methods"]}
    assert "Click" in method_names
    assert "repo_action" in cat["repo_method_reference"]["Click"]["mcp_tools"]


def test_winforms_framework_uses_swf_repo():
    from detection.framework_catalog import build_framework_catalog

    cat = build_framework_catalog(include_stored=False)
    wf = next(f for f in cat["frameworks"] if f["id"] == "winforms")
    assert wf["uses_swf_repo"] is True
    assert wf["uia_support"] == "partial"
