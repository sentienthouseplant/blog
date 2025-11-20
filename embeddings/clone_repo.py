# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "gitpython",
#     "click",
#     "semantic-text-splitter",
#     "tree-sitter-python",
#     "rich",
# ]
# ///


import contextlib
import tempfile
import os
from typing import Iterator, Tuple
import itertools

import git
import click
from semantic_text_splitter import CodeSplitter
import tree_sitter_python
from rich.table import Table
from rich.console import Console


@contextlib.contextmanager
def clone_repo(repo_owner: str, repo_name: str):
    with tempfile.TemporaryDirectory() as temp_dir:
        repo_auth_url = f"https://github.com/{repo_owner}/{repo_name}.git"
        repo = git.Repo.clone_from(repo_auth_url, temp_dir)
        yield repo


def chunk_repository(
    repo_owner: str, repo_name: str
) -> Iterator[Tuple[str, list[str]]]:
    splitter = CodeSplitter(tree_sitter_python.language(), (1000, 3000))
    with clone_repo(repo_owner, repo_name) as repo:
        for root, _, files in os.walk(repo.working_tree_dir):
            for file in files:
                if file.endswith(".py"):
                    file_path = os.path.join(root, file)
                    relative_path = os.path.relpath(file_path, repo.working_tree_dir)
                    with open(file_path, "r", encoding="utf-8") as f:
                        code = f.read()
                        chunks = splitter.chunks(code)
                        for chunk in chunks:
                            yield relative_path, chunk


@click.group()
def cli():
    pass


@cli.command()
@click.option("--repo-owner", required=True)
@click.option("--repo-name", required=True)
def tree(repo_owner: str, repo_name: str):
    with clone_repo(repo_owner, repo_name) as repo:
        for item in os.listdir(repo.working_tree_dir):
            print(item)


@cli.command()
@click.option("--repo-owner", required=True)
@click.option("--repo-name", required=True)
@click.option("--chunks", default=5, type=int)
def chunk(repo_owner: str, repo_name: str, chunks: int):
    console = Console()
    table = Table(title="Chunks", show_lines=True)
    table.add_column("File", style="cyan")
    table.add_column("Chunks", style="green")
    for file_path, chunk in itertools.islice(chunk_repository(repo_owner, repo_name), chunks):
        table.add_row(file_path, chunk)
    console.print(table)


if __name__ == "__main__":
    cli()
