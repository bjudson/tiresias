"""SQLite storage shared by the web app and Markdown importer."""
import os
import re
import sqlite3
from contextlib import contextmanager
from pathlib import Path


def database_path():
    return Path(os.environ.get("TIRESIAS_DB", "data/tiresias.sqlite3")).expanduser().resolve()


@contextmanager
def connect(path=None):
    path = Path(path) if path is not None else database_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(path, timeout=10)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA foreign_keys = ON")
    try:
        with db:
            yield db
    finally:
        db.close()


def initialize(path=None):
    with connect(path) as db:
        db.executescript("""
            CREATE TABLE IF NOT EXISTS claude_jobs (
                id INTEGER PRIMARY KEY, kind TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'running',
                dream_ids TEXT NOT NULL, results TEXT NOT NULL DEFAULT '[]', error TEXT
            );
            CREATE UNIQUE INDEX IF NOT EXISTS one_claude_job ON claude_jobs(status) WHERE status='running';
            CREATE TABLE IF NOT EXISTS dreams (
                id INTEGER PRIMARY KEY, title TEXT NOT NULL,
                date TEXT NOT NULL, body TEXT NOT NULL,
                metadata TEXT NOT NULL DEFAULT '{}',
                source TEXT UNIQUE, source_hash TEXT
            );
            CREATE TABLE IF NOT EXISTS dream_edits (
                dream_id INTEGER PRIMARY KEY REFERENCES dreams(id) ON DELETE CASCADE
            );
            CREATE TABLE IF NOT EXISTS symbols (
                slug TEXT PRIMARY KEY, title TEXT NOT NULL,
                summary TEXT NOT NULL DEFAULT '', body TEXT NOT NULL DEFAULT '',
                metadata TEXT NOT NULL DEFAULT '{}', source_hash TEXT
            );
            CREATE TABLE IF NOT EXISTS symbol_reflections (
                symbol_slug TEXT PRIMARY KEY REFERENCES symbols(slug),
                associations TEXT NOT NULL, interpretations TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS dream_symbols (
                dream_id INTEGER NOT NULL REFERENCES dreams(id) ON DELETE CASCADE,
                symbol_slug TEXT NOT NULL REFERENCES symbols(slug),
                PRIMARY KEY (dream_id, symbol_slug)
            );
            CREATE INDEX IF NOT EXISTS dreams_date ON dreams(date DESC, id DESC);
            CREATE INDEX IF NOT EXISTS symbols_dreams ON dream_symbols(symbol_slug);
        """)


def slugify(value):
    return re.sub(r"[^\w]+", "-", value.strip().lower(), flags=re.UNICODE).strip("-").replace("_", "-")


def set_symbols(db, dream_id, slugs):
    db.execute("DELETE FROM dream_symbols WHERE dream_id = ?", (dream_id,))
    for slug in dict.fromkeys(slugs):
        db.execute("INSERT OR IGNORE INTO symbols(slug, title) VALUES (?, ?)",
                   (slug, slug.replace("-", " ").capitalize()))
        db.execute("INSERT INTO dream_symbols VALUES (?, ?)", (dream_id, slug))


def list_dreams(db, symbol=None):
    return db.execute("""SELECT d.* FROM dreams d
        WHERE (? IS NULL OR EXISTS (SELECT 1 FROM dream_symbols ds
            WHERE ds.dream_id=d.id AND ds.symbol_slug=?))
        ORDER BY date DESC, id DESC""", (symbol, symbol)).fetchall()


def list_symbols(db):
    return db.execute("""SELECT s.*, COUNT(ds.dream_id) AS count FROM symbols s
        LEFT JOIN dream_symbols ds ON ds.symbol_slug=s.slug
        GROUP BY s.slug ORDER BY count DESC, s.title COLLATE NOCASE, s.slug""").fetchall()
