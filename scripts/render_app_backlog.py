#!/usr/bin/env python3
"""Regenerate apps/{slug}/backlog.md from backlog.json."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from app_backlog_lib import load_backlog, save_backlog, slug_from_app_name, write_backlog_md  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("app_name_or_slug", help='e.g. "Calculadora" or calculadora')
    args = parser.parse_args()
    raw = args.app_name_or_slug.strip()
    slug = slug_from_app_name(raw) if (" " in raw or raw[:1].isupper()) else raw.lower()
    backlog = load_backlog(slug)
    if not backlog:
        print(f"No backlog for slug '{slug}'", file=sys.stderr)
        return 1
    save_backlog(slug, backlog)
    out = write_backlog_md(slug, backlog)
    print(f"OK — {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
