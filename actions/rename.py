from lib import files


def _derive_title(slug: str) -> str:
    return " ".join(word.capitalize() for word in slug.split("-"))


def run(old_slug: str, new_slug: str, new_title: str | None = None) -> None:
    if old_slug == new_slug:
        print("Old and new slugs are identical.")
        return

    old_path = files.SYMBOLS_DIR / f"{old_slug}.md"
    new_path = files.SYMBOLS_DIR / f"{new_slug}.md"

    if not old_path.exists():
        print(f"Symbol not found: {old_slug}")
        return

    is_merge = new_path.exists()

    if is_merge:
        if new_title:
            print(f"Warning: --title ignored when merging into existing symbol `{new_slug}`.")
        old_path.unlink()
        print(f"Merged symbol: {old_slug} -> {new_slug} (existing target preserved; "
              f"old file deleted — recover from git if needed)")
    else:
        title = new_title or _derive_title(new_slug)
        files.rename_symbol_file(old_slug, new_slug, title)
        print(f"Renamed symbol: {old_slug} -> {new_slug} (title: {title!r})")

    changed = []
    for f in sorted(files.DREAMS_DIR.glob("*.md")):
        if files.replace_dream_symbol(f, old_slug, new_slug):
            changed.append(f.name)

    if changed:
        print(f"\nUpdated {len(changed)} dream(s):")
        for name in changed:
            print(f"  {name}")
    else:
        print("\nNo dreams referenced the old slug.")

    print(f"\nRun `audit` to surface dreams that now match `{new_slug}` more broadly.")
