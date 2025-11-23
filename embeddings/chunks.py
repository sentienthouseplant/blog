# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "gitpython",
#     "click",
#     "semantic-text-splitter",
#     "tree-sitter-python",
#     "rich",
#     "pydantic",
#     "pydantic-settings",
#     "openai",
#     "pinecone"
# ]
# ///


import contextlib
import functools
import itertools
import os
import tempfile
from string import Template
from typing import Iterator, Tuple

import click
import git
import tree_sitter_python
from openai import OpenAI
from pinecone import Pinecone
from pydantic_settings import BaseSettings
from rich.console import Console
from rich.table import Table
from semantic_text_splitter import CodeSplitter

PROMPT = Template("""
<document> 
$document
</document> 
Here is the chunk we want to situate within the whole document 
<chunk> 
$chunk
</chunk> 
Please give a short succinct context to situate this chunk within the overall document for the purposes of improving search retrieval of the chunk. Answer only with the succinct context and nothing else. 
""")


class Settings(BaseSettings):
    openrouter_api_key: str
    pinecone_api_key: str
    openrouter_base_url: str = "https://openrouter.ai/api/v1"


settings = Settings()


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
                        chunks = splitter.chunk_indices(code)
                        for chunk_index, chunk in chunks:
                            yield relative_path, code, chunk, chunk_index


def generate_chunk_context(code: str, chunk: str) -> str:
    prompt = PROMPT.substitute(document=code, chunk=chunk)
    response = OpenAI(
        api_key=settings.openrouter_api_key, base_url=settings.openrouter_base_url
    ).chat.completions.create(
        model="google/gemini-2.5-flash-lite",
        messages=[{"role": "user", "content": prompt}],
    )
    return response.choices[0].message.content


@functools.cache
def create_or_get_index(pinecone_client: Pinecone):
    already_exists = pinecone_client.has_index("codebase")
    if not already_exists:
        print("Creating index...")
        pinecone_client.create_index_for_model(
            name="codebase",
            cloud="aws",
            region="us-east-1",
            embed={"model": "llama-text-embed-v2", "field_map": {"text": "chunk_text"}},
        )
    return pinecone_client.Index("codebase")


def embed_chunk(
    pinecone_client: Pinecone,
    chunk_index: int,
    chunk_text: str,
    file_path: str,
    repo_owner: str,
    repo_name: str,
):
    index = create_or_get_index(pinecone_client)
    index.upsert_records(
        "default",
        [
            {
                "id": f"repo:{repo_owner}/{repo_name}:{file_path}:{chunk_index}",
                "chunk_text": chunk_text,
                "repo_owner": repo_owner,
                "repo_name": repo_name,
                "file_path": file_path,
            }
        ],
    )


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
    for file_path, _, chunk, _ in itertools.islice(
        chunk_repository(repo_owner, repo_name), chunks
    ):
        table.add_row(file_path, chunk)
    console.print(table)


@cli.command()
@click.option("--repo-owner", required=True)
@click.option("--repo-name", required=True)
@click.option("--chunks", default=5, type=int)
def enrich(repo_owner: str, repo_name: str, chunks: int):
    console = Console()
    table = Table(title="Enriched Chunks", show_lines=True)
    table.add_column("Path", style="cyan")
    table.add_column("Chunk", style="green")
    table.add_column("Context", style="green")
    with console.status("Enriching chunks..."):
        for file_path, code, chunk, _ in itertools.islice(
            chunk_repository(repo_owner, repo_name), chunks
        ):
            context = generate_chunk_context(code, chunk)
            table.add_row(
                file_path, chunk[:100] + "..." if len(chunk) > 30 else chunk, context
            )
    console.print(table)


@cli.command()
@click.option("--repo-owner", required=True)
@click.option("--repo-name", required=True)
@click.option("--chunks", default=5, type=int)
def embed(repo_owner: str, repo_name: str, chunks: int):
    console = Console()
    pinecone_client = Pinecone(api_key=settings.pinecone_api_key)
    with console.status("Embedding chunks..."):
        for file_path, code, chunk, chunk_index in itertools.islice(
            chunk_repository(repo_owner, repo_name), chunks if chunks > 0 else None
        ):
            context = generate_chunk_context(code, chunk)
            enriched_chunk = f"{context}\n\n{chunk}"
            embed_chunk(
                pinecone_client,
                chunk_index,
                enriched_chunk,
                file_path,
                repo_owner,
                repo_name,
            )


if __name__ == "__main__":
    cli()
