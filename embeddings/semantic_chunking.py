# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "semantic-text-splitter",
#     "tree-sitter-python",
#     "click",
#     "rich",
# ]
# ///

from pathlib import Path

import click
from semantic_text_splitter import CodeSplitter
import tree_sitter_python
from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax

console = Console()

@click.command()
@click.argument(
    "input_file",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
)
@click.option(
    "--chunk-size",
    type=int,
    default=500,
    show_default=True,
    help="Maximum number of characters per chunk.",
)
def semantic_chunking(input_file: Path, chunk_size: int) -> None:
    """Split a source file into semantic chunks and render them with rich formatting."""
    splitter = CodeSplitter(tree_sitter_python.language(), (chunk_size, 3000))
    code = input_file.read_text(encoding="utf-8")
    chunks = splitter.chunk_indices(code)

    console.rule(f"[bold cyan]Semantic chunks for[/] [green]{input_file}[/green]")

    original_panel = Panel(
        Syntax(code, "python", theme="monokai", line_numbers=True, word_wrap=True),
        title="[bold]Original File[/bold]",
        border_style="magenta",
        padding=(1, 2),
    )
    console.print(original_panel)

    if not chunks:
        console.print("[bold yellow]No chunks produced.[/bold yellow]")
        return

    console.rule("[bold cyan]Chunks[/bold cyan]")
    for chunk_index, (_, chunk_text) in enumerate(chunks, start=1):
        panel = Panel(
            Syntax(chunk_text, "python", theme="monokai", line_numbers=True, word_wrap=True),
            title=f"[bold]Chunk {chunk_index}[/bold]",
            border_style="cyan",
            padding=(1, 2),
        )
        console.print(panel)
        console.print()

if __name__ == "__main__":
    semantic_chunking()