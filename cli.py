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
    """Find all dreams tagged with a symbol and open them in VSCode."""
    from actions.find import run
    run(symbol_slug)


if __name__ == "__main__":
    dream()
