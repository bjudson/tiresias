#!/usr/bin/env python3
"""List all symbols ordered by number of dreams they appear in."""
from collections import defaultdict
from pathlib import Path

import frontmatter

JOURNAL_ROOT = Path(__file__).parent
DREAMS_DIR = JOURNAL_ROOT / "dreams"


def main() -> None:
    symbol_dreams: dict[str, list[str]] = defaultdict(list)

    for f in sorted(DREAMS_DIR.glob("*.md")):
        post = frontmatter.load(str(f))
        for slug in post.get("symbols") or []:
            symbol_dreams[slug].append(f.name)

    if not symbol_dreams:
        print("No symbols found.")
        return

    ranked = sorted(symbol_dreams.items(), key=lambda x: len(x[1]), reverse=True)

    for slug, dreams in ranked:
        print(f"{slug} ({len(dreams)})")
        for name in dreams:
            print(f"  {name}")


if __name__ == "__main__":
    main()
