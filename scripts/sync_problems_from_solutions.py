"""Sync problem HTML files into dbpshit-client/problems using dbpshit-scraper/solutions as the source of truth.

For each SQL solution in dbpshit-scraper/solutions/<section>/<name>.sql, this script
tries to find a matching problem HTML file in dbpshit-scraper/problems/<name>.html
and copies it into dbpshit-client/problems/<section>/<name>.html.
"""
from __future__ import annotations

import argparse
from pathlib import Path
from typing import Iterable


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Update dbpshit-client problems from dbpshit-scraper solutions.")
    parser.add_argument(
        "--scraper-root",
        type=Path,
        default=None,
        help="Path to dbpshit-scraper repository (default: sibling folder next to dbpshit-client).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show planned copies without writing files.",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Print each file action.",
    )
    return parser.parse_args()


def ensure_exists(paths: Iterable[Path]) -> None:
    for path in paths:
        if not path.exists():
            raise SystemExit(f"Missing expected path: {path}")


def main() -> None:
    args = parse_args()
    client_root = Path(__file__).resolve().parent
    scraper_root = (client_root.parent.parent / "dbpshit-scraper").resolve() if args.scraper_root is None else args.scraper_root.resolve()

    solutions_root = scraper_root / "solutions"
    problems_src_root = scraper_root / "problems"
    client_problems_root = client_root.parent / "problems"

    ensure_exists([scraper_root, solutions_root, problems_src_root, client_problems_root])

    total = copied = unchanged = missing = 0
    missing_ids: list[str] = []

    for section_dir in sorted(p for p in solutions_root.iterdir() if p.is_dir()):
        section_name = section_dir.name
        for sql_path in sorted(section_dir.glob("*.sql")):
            total += 1
            stem = sql_path.stem
            src_html = problems_src_root / f"{stem}.html"
            if not src_html.exists():
                missing += 1
                missing_ids.append(stem)
                if args.verbose:
                    print(f"[MISSING] {stem}")
                continue

            dest_dir = client_problems_root / section_name
            dest_dir.mkdir(parents=True, exist_ok=True)
            dest_path = dest_dir / src_html.name

            src_bytes = src_html.read_bytes()
            if dest_path.exists() and dest_path.read_bytes() == src_bytes:
                unchanged += 1
                if args.verbose:
                    rel = dest_path.relative_to(client_root)
                    print(f"[SKIP] {rel}")
                continue

            copied += 1
            if args.dry_run:
                if args.verbose:
                    rel = dest_path.relative_to(client_root)
                    print(f"[DRY] Would write {rel}")
            else:
                dest_path.write_bytes(src_bytes)
                if args.verbose:
                    rel = dest_path.relative_to(client_root)
                    print(f"[WRITE] {rel}")

    print(f"Total solutions scanned: {total}")
    print(f"Copied/updated: {copied}")
    print(f"Unchanged: {unchanged}")
    print(f"Missing problem HTML: {missing}")

    if missing_ids:
        print("Missing list (no matching problem HTML found):")
        for name in missing_ids:
            print(f" - {name}")


if __name__ == "__main__":
    main()
