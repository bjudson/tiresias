from collections import defaultdict
from lib import files, llm


def _collect_dreams_by_symbol() -> dict[str, list[dict]]:
    by_symbol: dict[str, list[dict]] = defaultdict(list)
    for f in sorted(files.DREAMS_DIR.glob("*.md")):
        post = files.read_dream(f)
        entry = {
            "date": post.get("date", f.stem),
            "title": post.get("title", ""),
            "content": post.content,
        }
        for slug in post.get("symbols") or []:
            by_symbol[slug].append(entry)
    return by_symbol


def run(target_slug: str | None = None, only_empty: bool = False) -> None:
    stubs = files.read_symbol_stubs()
    if target_slug:
        stubs = [s for s in stubs if s["slug"] == target_slug]
        if not stubs:
            print(f"Symbol not found: {target_slug}")
            return

    dreams_by_symbol = _collect_dreams_by_symbol()

    for stub in stubs:
        slug = stub["slug"]
        title = stub["title"] or slug
        dreams = dreams_by_symbol.get(slug, [])

        if not dreams:
            print(f"{slug}: skipped (no dreams)")
            continue

        if only_empty and stub["summary"]:
            print(f"{slug}: skipped (already has summary)")
            continue

        summary = llm.summarize_symbol(title, dreams)
        if not summary:
            print(f"{slug}: skipped (empty LLM response)")
            continue

        files.update_symbol_summary(slug, summary)
        print(f"{slug} ({len(dreams)} dream{'s' if len(dreams) != 1 else ''}): {summary}")
