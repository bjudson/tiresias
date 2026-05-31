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


if __name__ == "__main__":
    dream()
