# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
uv sync                                   # Install dependencies
uv run python cli.py --help               # Show available CLI commands
uv run python cli.py extract <dream.md>   # Extract symbols from a dream file
uv run python cli.py find <symbol-slug>   # Find all dreams containing a symbol
uv run python list_symbols.py             # List symbols ranked by frequency
```

Requires `ANTHROPIC_API_KEY` in `.env` (see `.env.example`).

## Architecture

The project is a personal dream journaling CLI. It uses Claude to extract recurring symbolic imagery from dream narratives, matched against an existing symbol inventory.

**Layers:**
- `cli.py` — Click entry point, dispatches to actions
- `actions/` — Business logic for each command (`extract.py`, `find.py`)
- `lib/files.py` — Filesystem abstraction for reading/writing dream and symbol files
- `lib/llm.py` — Anthropic API wrapper; `extract_symbols()` sends CONVENTIONS.md as the system prompt and returns JSON with matched/new symbols

**Data flow for `extract`:** read dream file → load symbol stubs → call Claude → create new symbol stub files + update dream frontmatter with symbol list.

**Data flow for `find`:** scan all dream files for a symbol slug in frontmatter → aggregate matches into a temp file → open in VSCode.

## Data Format

Dreams live in `dreams/YYYY-MM-DD - slug.md` and symbols in `symbols/<slug>.md`. Both use YAML frontmatter + Markdown body. The schema and symbol extraction rules are defined in `CONVENTIONS.md`, which is also fed verbatim to Claude as the system prompt in `lib/llm.py`.

`lib/files.py` uses a custom YAML dumper to preserve frontmatter key insertion order (not alphabetical).
