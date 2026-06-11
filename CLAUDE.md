# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
uv sync                            # Install dependencies
uv run dream --help                # Show available CLI commands
uv run dream extract <dream.md>    # Extract symbols from a dream file
uv run dream find <symbol-slug>    # Find all dreams containing a symbol
uv run dream symbols               # List symbols ranked by frequency
uv run dream audit                 # Audit all dreams for missing symbol connections
uv run dream rename <old> <new>    # Rename a symbol slug across all dreams (merges if target exists)
uv run dream summarize             # Generate symbol summaries from their dreams (--symbol, --only-empty)
```

Requires `ANTHROPIC_API_KEY` in `.env` (see `.env.example`).

## Architecture

The project is a personal dream journaling CLI. It uses Claude to extract recurring symbolic imagery from dream narratives, matched against an existing symbol inventory.

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
