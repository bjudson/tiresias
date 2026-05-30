import shutil
import subprocess
from pathlib import Path
from lib import files

_CODE = (
    shutil.which("code")
    or "/Applications/Visual Studio Code.app/Contents/Resources/app/bin/code"
)


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

    tmp_path = Path(f"/tmp/symbol-{slug}.md")
    lines = [f"# Dreams containing symbol: {slug}\n"]
    for f, post in matches:
        date = post.get("date", f.stem)
        title = post.get("title", "")
        header = f"## {date}" + (f" — {title}" if title else "")
        lines.append(header)
        lines.append("")
        lines.append(post.content.strip())
        lines.append("")

    tmp_path.write_text("\n".join(lines))
    subprocess.run([_CODE, str(tmp_path)])
