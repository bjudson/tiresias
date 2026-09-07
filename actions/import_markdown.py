"""Atomic, repeatable import; Markdown remains untouched."""
import hashlib
import json
from datetime import date
from pathlib import Path

import frontmatter

from lib.database import connect, initialize, set_symbols


def run(root: Path, database=None):
    root = root.resolve()
    if not (root / "dreams").is_dir():
        raise ValueError(f"No dreams directory in {root}")
    initialize(database)
    counts = {"dreams_added": 0, "dreams_updated": 0, "dreams_skipped": 0, "symbols_updated": 0}
    with connect(database) as db:
        for kind in ("symbols", "dreams"):
            for path in sorted((root / kind).glob("*.md")):
                try:
                    raw = path.read_text(encoding="utf-8")
                    post = frontmatter.loads(raw)
                    digest = hashlib.sha256(raw.encode()).hexdigest()
                    metadata = json.dumps(post.metadata, default=str, ensure_ascii=False)
                    if kind == "symbols":
                        slug = path.stem
                        previous = db.execute("SELECT source_hash FROM symbols WHERE slug=?", (slug,)).fetchone()
                        if previous and previous[0] == digest:
                            continue
                        db.execute("""INSERT INTO symbols(slug,title,summary,body,metadata,source_hash)
                            VALUES (?,?,?,?,?,?) ON CONFLICT(slug) DO UPDATE SET
                            title=excluded.title, summary=excluded.summary, body=excluded.body,
                            metadata=excluded.metadata, source_hash=excluded.source_hash""",
                            (slug, str(post.get("title") or slug), str(post.get("summary") or ""), post.content, metadata, digest))
                        counts["symbols_updated"] += 1
                        continue
                    dream_date = date.fromisoformat(str(post.get("date", path.name[:10]))).isoformat()
                    title = str(post.get("title") or path.stem).strip()
                    slugs = post.get("symbols") or []
                    if not isinstance(slugs, list) or any(not isinstance(s, str) or not s.strip() or "/" in s for s in slugs):
                        raise ValueError("symbols must be a list of nonempty slugs without slashes")
                    source = path.relative_to(root).as_posix()
                    previous = db.execute("SELECT id, source_hash FROM dreams WHERE source=?", (source,)).fetchone()
                    if previous and (previous["source_hash"] == digest or db.execute(
                        "SELECT 1 FROM dream_edits WHERE dream_id=?", (previous["id"],)
                    ).fetchone()):
                        counts["dreams_skipped"] += 1
                        continue
                    if previous:
                        dream_id = previous["id"]
                        db.execute("UPDATE dreams SET title=?,date=?,body=?,metadata=?,source_hash=? WHERE id=?",
                                   (title, dream_date, post.content, metadata, digest, dream_id))
                        counts["dreams_updated"] += 1
                    else:
                        dream_id = db.execute("INSERT INTO dreams(title,date,body,metadata,source,source_hash) VALUES (?,?,?,?,?,?)",
                            (title, dream_date, post.content, metadata, source, digest)).lastrowid
                        counts["dreams_added"] += 1
                    set_symbols(db, dream_id, slugs)
                except Exception as exc:
                    raise ValueError(f"{path}: {exc}") from exc
    return counts
