from pathlib import Path
from lib import files, llm


def run(dream_path: Path) -> None:
    post = files.read_dream(dream_path)
    dream_text = post.content

    existing = files.read_symbol_stubs()
    result = llm.extract_symbols(dream_text, existing)

    matched = result.get("matched", [])
    new_symbols = result.get("new", [])

    for sym in new_symbols:
        files.write_symbol_stub(sym["slug"], sym["title"], sym["summary"])
        print(f"Created symbol: {sym['slug']}")

    for slug in matched:
        print(f"Matched symbol: {slug}")

    new_slugs = matched + [s["slug"] for s in new_symbols]
    files.update_dream_symbols(dream_path, new_slugs)
    print(f"Updated {dream_path.name} — symbols: {new_slugs}")
