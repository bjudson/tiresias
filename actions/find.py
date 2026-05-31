from lib import files

DERIVED_DIR = files.DREAMS_DIR.parent / "derived"


def run(slug: str) -> None:
    matches = []
    for f in sorted(files.DREAMS_DIR.glob("*.md")):
        post = files.read_dream(f)
        symbols = list(post.get("symbols") or [])
        if slug in symbols:
            matches.append((f, post))

    if not matches:
        print(f"No dreams found with symbol: {slug}")
        return

    DERIVED_DIR.mkdir(exist_ok=True)
    out_path = DERIVED_DIR / f"symbol-{slug}.md"
    lines = [f"# Dreams containing symbol: {slug}\n"]
    for f, post in matches:
        date = post.get("date", f.stem)
        title = post.get("title", "")
        header = f"## {date}" + (f" — {title}" if title else "")
        lines.append(header)
        lines.append("")
        lines.append(post.content.strip())
        lines.append("")

    out_path.write_text("\n".join(lines))
    print(out_path)
