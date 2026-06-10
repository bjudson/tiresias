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


if __name__ == "__main__":
    dream()
