"""Archive MCP improvement proposals by Estado (aplicada/aceptada/rechazada)."""
from __future__ import annotations

import argparse
import re
import shutil
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
IMPROVEMENT_ROOT = REPO_ROOT / "_MCP_IMPROVEMENT"
SOURCE_DIRS = ("mejoras-skill", "mejoras-tool", "mejoras-codigo")
ESTADO_RE = re.compile(
    r"^\|\s*\*\*Estado\*\*\s*\|\s*([^\|]+?)\s*\|",
    re.IGNORECASE | re.MULTILINE,
)


def parse_estado(text: str) -> str:
    match = ESTADO_RE.search(text)
    if not match:
        return ""
    raw = match.group(1).strip().lower()
    token = raw.split()[0] if raw else ""
    if token.startswith("aplicada"):
        return "aplicada"
    if token.startswith("aceptada"):
        return "aceptada"
    if token.startswith("rechazada"):
        return "rechazada"
    if token.startswith("propuesta"):
        return "propuesta"
    return token


def archive_dest(estado: str, source_dir: str) -> str | None:
    if estado in ("aplicada", "aceptada"):
        return "aceptadas"
    if estado == "rechazada":
        return "rechazadas"
    return None


def collect_moves(*, dry_run: bool = False) -> list[dict]:
    moves: list[dict] = []
    for source_dir in SOURCE_DIRS:
        src_root = IMPROVEMENT_ROOT / source_dir
        if not src_root.is_dir():
            continue
        for path in sorted(src_root.glob("*.md")):
            estado = parse_estado(path.read_text(encoding="utf-8"))
            bucket = archive_dest(estado, source_dir)
            if not bucket:
                continue
            dest = IMPROVEMENT_ROOT / bucket / source_dir / path.name
            moves.append({
                "source": path,
                "dest": dest,
                "estado": estado,
                "bucket": bucket,
            })
    return moves


def run_archive(*, dry_run: bool = False) -> dict:
    moves = collect_moves(dry_run=dry_run)
    archived = 0
    for item in moves:
        dest: Path = item["dest"]
        if not dry_run:
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(item["source"]), str(dest))
        archived += 1
    return {
        "dry_run": dry_run,
        "archived": archived,
        "moves": [
            {
                "from": str(m["source"].relative_to(REPO_ROOT)),
                "to": str(m["dest"].relative_to(REPO_ROOT)),
                "estado": m["estado"],
            }
            for m in moves
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Move applied/accepted/rejected MCP improvements out of mejoras-*/",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="List moves without writing files",
    )
    args = parser.parse_args()
    result = run_archive(dry_run=args.dry_run)
    prefix = "Would archive" if result["dry_run"] else "Archived"
    print(f"{prefix}: {result['archived']} file(s)")
    for move in result["moves"]:
        print(f"  [{move['estado']}] {move['from']} -> {move['to']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
