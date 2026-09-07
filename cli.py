#!/usr/bin/env python3
import click
from pathlib import Path


@click.group()
def dream():
    pass


@dream.command()
@click.argument("dream_file", type=click.Path(exists=True, path_type=Path))
def extract(dream_file):
    """Extract symbols from a dream file and update the symbols directory."""
    from actions.extract import run
    run(dream_file)


@dream.command()
@click.argument("symbol_slug")
def find(symbol_slug):
    """Find all dreams tagged with a symbol and save to derived/."""
    from actions.find import run
    run(symbol_slug)


@dream.command()
def symbols():
    """List all symbols ranked by number of dreams."""
    from actions.symbols import run
    run()


@dream.command()
def audit():
    """Audit all dreams for missing symbol connections."""
    from actions.audit import run
    run()


@dream.command()
@click.option(
    "--symbol",
    "target_slug",
    default=None,
    help="Summarize a single symbol.",
)
@click.option(
    "--only-empty",
    is_flag=True,
    help="Skip symbols that already have a summary.",
)
def summarize(target_slug, only_empty):
    """Generate symbol summaries from the dreams they appear in."""
    from actions.summarize import run
    run(target_slug, only_empty)


@dream.command()
@click.argument("old_slug")
@click.argument("new_slug")
@click.option(
    "--title",
    "new_title",
    default=None,
    help="Override title (default: derived from new slug).",
)
def rename(old_slug, new_slug, new_title):
    """Rename a symbol and update its slug across all dreams.

    If the target slug already exists, merges into it.
    """
    from actions.rename import run
    run(old_slug, new_slug, new_title)


@dream.command()
@click.option("--port", default=8000, type=click.IntRange(1, 65535), show_default=True)
@click.option("--reload", is_flag=True, help="Reload when Python files change.")
def serve(port, reload):
    """Run the local web journal at http://127.0.0.1:8000."""
    import uvicorn
    uvicorn.run("web.app:app", host="127.0.0.1", port=port, reload=reload)


@dream.command("import-markdown")
@click.argument("root", default=".", type=click.Path(exists=True, file_okay=False, path_type=Path))
def import_markdown(root):
    """Import ROOT/dreams and ROOT/symbols into SQLite (safe to repeat)."""
    from actions.import_markdown import run
    try:
        result = run(root)
    except ValueError as exc:
        raise click.ClickException(str(exc)) from exc
    click.echo(", ".join(f"{key}: {value}" for key, value in result.items()))


if __name__ == "__main__":
    dream()
