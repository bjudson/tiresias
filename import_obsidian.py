#!/usr/bin/env python3
"""One-off import script: converts Obsidian dream files into journal format."""
import re
import sys
from pathlib import Path

import frontmatter
from frontmatter.default_handlers import YAMLHandler


class _UnsortedYAMLHandler(YAMLHandler):
    def export(self, metadata, **kwargs):
        kwargs.setdefault("sort_keys", False)
        return super().export(metadata, **kwargs)


_handler = _UnsortedYAMLHandler()


def _dumps(post: frontmatter.Post) -> str:
    return frontmatter.dumps(post, handler=_handler)


JOURNAL_ROOT = Path(__file__).parent
DREAMS_DIR = JOURNAL_ROOT / "dreams"
SYMBOLS_DIR = JOURNAL_ROOT / "symbols"

TAG_RE = re.compile(r"#([A-Za-z][A-Za-z0-9_-]*)")


def slugify(text: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower())
    return re.sub(r"-+", "-", slug).strip("-")


def title_from_slug(slug: str) -> str:
    return " ".join(word.capitalize() for word in slug.split("-"))


def write_symbol_stub(slug: str) -> bool:
    """Write stub if absent. Returns True if created."""
    path = SYMBOLS_DIR / f"{slug}.md"
    if path.exists():
        return False
    SYMBOLS_DIR.mkdir(exist_ok=True)
    post = frontmatter.Post(
        "",
        title=title_from_slug(slug),
        slug=slug,
        summary="",
        associations=[],
        interpretations=[],
    )
    path.write_text(_dumps(post))
    return True


def parse_obsidian_file(
    obsidian_file: Path,
) -> tuple[str, str, str, list[str]]:
    """Return (date, title, content, slugs)."""
    stem = obsidian_file.stem
    parts = stem.split(" - ", 1)
    date = parts[0].strip()
    title = parts[1].strip() if len(parts) > 1 else ""

    raw = obsidian_file.read_text()
    lines = raw.splitlines()
    for i, line in enumerate(lines):
        if line.strip() == "---":
            lines = lines[:i]
            break
    content = "\n".join(lines).strip()

    slugs = list(dict.fromkeys(
        slugify(t) for t in TAG_RE.findall(content)
    ))
    return date, title, content, slugs


def main(obsidian_dir: str) -> None:
    source = Path(obsidian_dir)
    if not source.is_dir():
        print(f"Not a directory: {source}", file=sys.stderr)
        sys.exit(1)

    files = sorted(
        f for f in source.glob("*.md") if not f.name.startswith(".")
    )
    if not files:
        print("No .md files found.")
        return

    parsed = [parse_obsidian_file(f) for f in files]

    DREAMS_DIR.mkdir(exist_ok=True)

    print(f"Importing {len(files)} dreams from {source}...")
    for date, title, content, slugs in parsed:
        new_symbols = [s for s in slugs if write_symbol_stub(s)]

        dest = DREAMS_DIR / f"{date} - {slugify(title)}.md"
        post = frontmatter.Post(content, date=date, title=title, symbols=slugs)
        dest.write_text(_dumps(post))

        symbol_note = f" [{', '.join(slugs)}]" if slugs else ""
        new_note = f" (+{', '.join(new_symbols)})" if new_symbols else ""
        print(f"  {dest.name}{symbol_note}{new_note}")

    print("Done.")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(f"Usage: uv run python {sys.argv[0]} <obsidian-dreams-dir>")
        sys.exit(1)
    main(sys.argv[1])
