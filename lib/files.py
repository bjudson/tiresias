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


JOURNAL_ROOT = Path(__file__).parent.parent
DREAMS_DIR = JOURNAL_ROOT / "dreams"
SYMBOLS_DIR = JOURNAL_ROOT / "symbols"


def read_dream(path: Path) -> frontmatter.Post:
    return frontmatter.load(str(path))


def read_symbol_stubs() -> list[dict]:
    """Return {slug, title, summary} from frontmatter of every symbol file."""
    stubs = []
    for f in sorted(SYMBOLS_DIR.glob("*.md")):
        post = frontmatter.load(str(f))
        stubs.append({
            "slug": f.stem,
            "title": post.get("title", ""),
            "summary": post.get("summary", ""),
        })
    return stubs


def write_symbol_stub(slug: str, title: str, summary: str) -> None:
    """Write a new symbol stub file. No-op if the file already exists."""
    path = SYMBOLS_DIR / f"{slug}.md"
    if path.exists():
        return
    SYMBOLS_DIR.mkdir(exist_ok=True)
    post = frontmatter.Post(
        "",
        title=title,
        slug=slug,
        summary=summary,
        associations=[],
        interpretations=[],
    )
    path.write_text(_dumps(post))


def update_dream_symbols(path: Path, new_slugs: list[str]) -> None:
    """Union new_slugs into the dream's symbols frontmatter list."""
    post = frontmatter.load(str(path))
    existing = list(post.get("symbols") or [])
    combined = list(dict.fromkeys(existing + new_slugs))
    post["symbols"] = combined
    path.write_text(_dumps(post))
