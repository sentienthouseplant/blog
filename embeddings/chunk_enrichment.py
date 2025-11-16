# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "semantic-text-splitter",
#     "tree-sitter-python",
#     "click",
#     "rich",
#     "openai",
#     "pydantic",
#     "pydantic-settings",
# ]
# ///


from pydantic_settings import BaseSettings
from string import Template
import click
from pathlib import Path
from semantic_text_splitter import CodeSplitter
import tree_sitter_python
from openai import OpenAI
from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax


PROMPT = Template("""
Here is the document the user will chunk. Use this document to generate the context for the chunk:
<document> 
$document
</document>

Here is the chunk we want to situate within the document above.
<chunk> 
$chunk
</chunk> 
Please give a short succinct context to situate this chunk within the overall document for the purposes of improving search retrieval of the chunk. Answer only with the succinct context and nothing else.
""")

class Settings(BaseSettings):
    openrouter_api_key: str
    openrouter_base_url: str = "https://openrouter.ai/api/v1"

settings = Settings()
console = Console()

def chunk_file(input_file: Path, chunk_size: int) -> str:
    splitter = CodeSplitter(tree_sitter_python.language(), (500, 3000))
    code = input_file.read_text(encoding="utf-8")
    chunks = splitter.chunks(code)
    return chunks

def create_context(document: str, chunk: str) -> str:
    prompt = PROMPT.substitute(document=document, chunk=chunk)
    console.print(prompt)
    response = OpenAI(api_key=settings.openrouter_api_key, base_url=settings.openrouter_base_url).chat.completions.create(
        model="google/gemini-2.5-flash-lite-preview-09-2025",
        messages=[
            {
                "role": "system",
                "content": prompt,
            },
        ],
    )
    context = response.choices[0].message.content
    return context


@click.command()
@click.argument("input_file", type=click.Path(exists=True, dir_okay=False, path_type=Path), required=False, default=None)
@click.option("--chunk-text", required=False, default=None)
@click.option("--document-text", required=False, default=None)
def chunk_enrichment(input_file: Path | None = None, chunk_text: str | None = None, document_text: str | None = None) -> None:
    if chunk_text is None:
        chunks = chunk_file(input_file, 500)
    else:
        chunks = [chunk_text]
    if document_text is None:
        document_text = input_file.read_text(encoding="utf-8")
    else:
        document_text = document_text
    for idx, chunk_text in enumerate(chunks, 1):
        context = create_context(document_text, chunk_text)
        
        # Display chunk with syntax highlighting
        syntax = Syntax(chunk_text, "python", theme="monokai", line_numbers=True)
        console.print(Panel(
            syntax,
            title=f"[bold cyan]📦 Chunk {idx}[/bold cyan]",
            border_style="cyan",
            expand=False
        ))
        
        # Display context
        console.print(Panel(
            f"[italic]{context}[/italic]",
            title="[bold green]🔍 Context[/bold green]",
            border_style="green",
            expand=False
        ))
        
        console.print()  # Add spacing between chunks

if __name__ == "__main__":
    chunk_enrichment()
