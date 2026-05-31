from datetime import date
from lib import files, llm

DERIVED_DIR = files.DREAMS_DIR.parent / "derived"


def run() -> None:
    all_symbols = files.read_symbol_stubs()
    if not all_symbols:
        print("No symbols in inventory yet.")
        return

    dream_files = sorted(files.DREAMS_DIR.glob("*.md"))
    if not dream_files:
        print("No dreams found.")
        return

    changes: list[tuple[str, list[str]]] = []

    for f in dream_files:
        post = files.read_dream(f)
        already_tagged = list(post.get("symbols") or [])

        missing = llm.audit_symbols(post.content, already_tagged, all_symbols)

        if missing:
            files.update_dream_symbols(f, missing)
            changes.append((f.name, missing))
            print(f"{f.name}: added {missing}")
        else:
            print(f"{f.name}: ok")

    DERIVED_DIR.mkdir(exist_ok=True)
    out_path = DERIVED_DIR / f"audit-{date.today()}.md"
    lines = [f"# Symbol Audit — {date.today()}\n"]

    if changes:
        lines.append(f"{len(changes)} dream(s) updated, "
                     f"{sum(len(m) for _, m in changes)} new connection(s).\n")
        for name, missing in changes:
            lines.append(f"## {name}")
            for slug in missing:
                lines.append(f"- {slug}")
            lines.append("")
    else:
        lines.append("No missing connections found.")

    out_path.write_text("\n".join(lines))
    print(f"\nSaved audit to {out_path}")
