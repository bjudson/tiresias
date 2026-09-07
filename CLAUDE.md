# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
uv sync                            # Install dependencies
uv run dream serve                 # Local web app at 127.0.0.1:8000
uv run dream import-markdown        # Import dreams/ and symbols/ into SQLite
uv run pytest                      # Test import and web flows
uv run dream --help                # Show available CLI commands
uv run dream extract <dream.md>    # Extract symbols from a dream file
uv run dream find <symbol-slug>    # Find all dreams containing a symbol
uv run dream symbols               # List symbols ranked by frequency
uv run dream audit                 # Audit all dreams for missing symbol connections
uv run dream rename <old> <new>    # Rename a symbol slug across all dreams (merges if target exists)
uv run dream summarize             # Generate symbol summaries from their dreams (--symbol, --only-empty)
```

Basic web journaling requires no API key; web Claude extraction and audits use the same `.env` key as the CLI. Legacy LLM commands require `ANTHROPIC_API_KEY` in `.env` (see `.env.example`).

## Architecture

The project is a local FastAPI/HTMX/Tailwind dream journal with SQLite storage and a legacy Markdown CLI.

**Web layers:**
- `web/app.py` — app factory, form validation, local-only host/origin checks, routes
- `web/templates/` — shared base, journal (`/?symbol=slug` filter), and standalone symbol detail (`/symbols/slug/`) with HTMX progressive enhancement
- `symbol_reflections` table — web-edited associations/interpretations, overriding imported metadata without being overwritten on re-import
- `web/static/` — bundled assets, rebuilt with `npm ci && npm run build`
- `lib/database.py` — SQLite schema and query helpers (`TIRESIAS_DB`, default `data/tiresias.sqlite3`)
- `actions/import_markdown.py` — atomic, repeatable Markdown import preserving metadata
- `tests/test_web.py` — isolated temporary database tests

Dream editing uses `/dreams/{id}/edit`; the `dream_edits` table protects web-edited dreams from later Markdown imports.

SQLite owns web entries; legacy commands operate only on Markdown. Re-import to synchronize source changes into SQLite; there is no reverse sync. It uses Claude to extract recurring symbolic imagery from dream narratives, matched against an existing symbol inventory.

**Layers:**
- `cli.py` — Click entry point, dispatches to actions
- `actions/` — Business logic for each command (`extract.py`, `find.py`, `symbols.py`)
- `lib/files.py` — Filesystem abstraction for reading/writing dream and symbol files
- `lib/llm.py` — Anthropic API wrapper; `extract_symbols()` sends CONVENTIONS.md as the system prompt and returns JSON with matched/new symbols

**Data flow for `extract`:** read dream file → load symbol stubs → call Claude → create new symbol stub files + update dream frontmatter with symbol list.

**Data flow for `find`:** scan all dream files for a symbol slug in frontmatter → aggregate matches into `derived/symbol-<slug>.md`.

## Data Format

Dreams live in `dreams/YYYY-MM-DD - slug.md` and symbols in `symbols/<slug>.md`. Both use YAML frontmatter + Markdown body. The schema and symbol extraction rules are defined in `CONVENTIONS.md`, which is also fed verbatim to Claude as the system prompt in `lib/llm.py`.

`lib/files.py` uses a custom YAML dumper to preserve frontmatter key insertion order (not alphabetical).

Web Claude actions: `lib/claude_jobs.py` runs sequential background work through `lib/llm.py`; `claude_jobs` persists progress/results, and `/claude/{id}` polls with HTMX. Only one action runs at a time. Tests mock Claude; avoid live API calls during routine verification.
