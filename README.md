# Tiresias

This is a very simple personal project to explore connections in dreams using LLMs. Currently it is configured to use Claude. 

## Philosophy

Terisias is a pretty opinionated project. It was inspired by James Hillman's book [The Dream and the Underworld](https://archive.org/details/dreamunderworld00hill), which encourages letting the dream image have a life of its own, without reducing it to rationalistic interpretation. Terisias calls LLMs to help find connections between dreams on a symbolic level, without relying on the model for meaning making. I explicitly ground the prompts using Hillman, but it would be easy to use the same principles with a different approach to dream exploration. The main thing we avoid is leaning on the model for symbolic analysis, which is reductive, and outsources soul-making.

The challenge with the typical design of off the shelf LLM tools is tracking past insights and incorporating them into new analysis. In Tiresias, symbol files are used to organize the text and layer on meaning.

Ultimately, I hope to uncover patterns that could be helpful for exploring any complex, symbolic text regardless of interpretive framework.

## Local web app

Requires Python 3.13+ and [uv](https://docs.astral.sh/uv/). From this repository:

```bash
uv sync
uv run dream import-markdown
uv run dream serve
```

Open **http://127.0.0.1:8000**. The app binds to the loopback interface. Adding, editing, and browsing dreams works without an API key or external service. Claude actions require `ANTHROPIC_API_KEY` in `.env`. Node and a CDN are not needed to run the app.

The landing page has a new-dream form, a newest-first dream list (ties use insertion order, newest first), and symbols ranked by the number of dreams that reference them. Enter optional symbols separated by commas; names become lowercase hyphenated slugs. Click a dream to read its narrative, date, and symbols. Use **Edit dream** to update its title, date, narrative, or symbols; save changes or cancel to return to the dream. Click a symbol in the frequency list to filter the journal using `/?symbol=music`. Click a symbol pill on a dream, or the symbol heading above a filtered list, to open `/symbols/music/`: symbol information at the top, full related dream narratives below, and an associations/interpretations editor on the right (stacked on mobile). Enter one reflection per line; edit or remove lines and save. Imported reflections prefill the form; web edits persist separately in SQLite and survive subsequent Markdown imports. Links have direct URLs and work with or without JavaScript; HTMX enhances navigation and form submissions. Narratives are displayed as escaped plain text, preserving line breaks and any original Markdown notation.

Use `uv run dream serve --reload` during development, or `--port 8001` to select another port.

### SQLite and importing Markdown

The default database is `data/tiresias.sqlite3`, relative to the working directory. Override it with `TIRESIAS_DB` (an environment variable, not automatically loaded from `.env`):

```bash
TIRESIAS_DB=/absolute/path/journal.sqlite3 uv run dream import-markdown /path/to/journal
TIRESIAS_DB=/absolute/path/journal.sqlite3 uv run dream serve
```

The import root must contain `dreams/` and may contain `symbols/`. The importer reads YAML frontmatter and Markdown bodies, preserving all original metadata as JSON, including symbol associations and interpretations. Missing symbol files become stubs. Dates must be valid ISO dates; absent dates fall back to the filename prefix. Invalid input reports its filename and rolls back the entire import.

Imports are repeatable: relative dream filenames identify imported entries, and content hashes detect changes. Unchanged files are skipped; changed files replace the corresponding imported dream and its tags unless the dream has been edited in the web app. Web-edited dreams are skipped on subsequent imports so your edits are preserved. Symbol files update summaries, notes, and metadata by filename slug. Source Markdown is never modified. Renaming a source dream file creates a new imported entry; deleting a source file does not delete its database entry. Use one journal source per database.

**SQLite is the web app's source of truth.** New web entries are not written to Markdown. The legacy LLM commands below continue to work on Markdown; rerun the import to bring their changes into SQLite. Deletion, export, and further web-based analysis are outside this version.

To back up: stop the server and copy `data/tiresias.sqlite3` (or your configured database) somewhere safe. Restore by copying it back while the server is stopped. Database files and journal Markdown are excluded from Git.

### Claude actions

Set `ANTHROPIC_API_KEY` in `.env` and restart the server. On a dream detail page, **Extract symbols with Claude** matches existing symbols and creates new ones using `lib/llm.py`. **Audit all dreams with Claude** in the header checks each dream sequentially against the current symbol inventory, adding missing existing symbols. These actions send dream narratives and the symbol inventory to Anthropic and use your API account.

Each action opens a results URL (`/claude/<id>`) that updates automatically while it runs. It lists symbols added to each dream, newly created symbols, existing associations, and errors. Results persist in SQLite and can be revisited at that URL. Only one Claude action runs at a time; another click opens the active action. Keep the server running during an audit. A server restart marks an unfinished action as stopped; completed additions remain saved. Run the action again to check remaining connections.

Existing tags are preserved. Dreams modified while Claude is working are skipped. Claude-tagged dreams receive the same re-import protection as manually edited dreams. Failed or invalid responses do not apply partial changes to the current dream. Use the standard single-process `dream serve` command for this local background-job implementation.

### Development

```bash
uv sync
uv run pytest
```

Templates live in `web/templates/`, routes in `web/app.py`, storage in `lib/database.py`, and the importer in `actions/import_markdown.py`. Every connection enables SQLite foreign keys and closes after its transaction. Tables are initialized at server startup or import; future schema changes will need migrations.

Compiled Tailwind CSS and HTMX are checked into `web/static/`, so Node is only needed when rebuilding assets:

```bash
npm ci
npm run build
```

This uses the [Tailwind CLI](https://tailwindcss.com/docs/installation/tailwind-cli) and [HTMX boosted navigation](https://htmx.org/attributes/hx-boost/). Package versions are pinned in `package-lock.json`; Python versions are locked in `uv.lock`.

## Legacy Markdown CLI

These commands require `ANTHROPIC_API_KEY` in `.env` when they call Claude:

1. `uv run dream extract <dream.md>` — extract symbols and tag the Markdown dream
2. `uv run dream find <symbol>` — aggregate matching Markdown dreams into `derived/`
3. `uv run dream symbols` — rank symbols in Markdown dreams by frequency
4. `uv run dream audit` — scan Markdown dreams for missed symbol connections
5. `uv run dream rename <old> <new>` — rename or merge a Markdown symbol
6. `uv run dream summarize` — generate symbol summaries (`--symbol`, `--only-empty`)

The Markdown schema and extraction principles remain in `CONVENTIONS.md`.
