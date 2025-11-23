# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "rich"
# ]
# ///

from time import sleep

from rich.console import Console

console = Console()

with console.status(":wave: Hello, world!") as status:
    sleep(1)
