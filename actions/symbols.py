from collections import defaultdict
from lib import files


def run() -> None:
    symbol_dreams: dict[str, list[str]] = defaultdict(list)

    for f in sorted(files.DREAMS_DIR.glob("*.md")):
        post = files.read_dream(f)
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
